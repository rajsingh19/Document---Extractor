import math
import re
from collections import Counter
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.copilot import (
    RAGMetric, RAGContext, SourceContext, InsightContext, DocumentContext,
    ReviewContext, CopilotSummary
)
from backend.app.services.insights_service import insights_service
from backend.app.services.copilot_recommendations import copilot_recommendation_service
from backend.app.services.copilot_attention import copilot_attention_service

# ---------------------------------------------------------------------------
# Schemas (Phase 3 & Phase 14)
# ---------------------------------------------------------------------------

class RAGDocumentChunk(BaseModel):
    """
    Strongly typed internal representation of a document chunk.
    Preserves exact document identity, page, and lineage metadata.
    """
    chunk_id: str = Field(..., description="Deterministic unique identifier for the chunk")
    document_id: int = Field(..., description="Foreign key to documents.id")
    document_name: str = Field(..., description="Document filename for provenance")
    document_type: Optional[str] = Field(default=None, description="Classified document category")
    page: Optional[int] = Field(default=None, description="1-indexed page number if available")
    text: str = Field(..., description="Clean textual content of the chunk")
    reporting_period: Optional[str] = Field(default=None, description="Document reporting period if known")
    source_field: str = Field(default="extracted_text", description="Source lineage origin")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RAGChunkResult(BaseModel):
    """
    Retrieved chunk result containing original metadata and similarity score.
    Never flattens into raw text; retains complete source lineage.
    """
    chunk_id: str
    document_id: int
    document_name: str
    document_type: Optional[str] = None
    page: Optional[int] = None
    text: str
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    reporting_period: Optional[str] = None
    source_field: str = Field(default="extracted_text")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Document Chunker (Phase 4, 5, 6, 7)
# ---------------------------------------------------------------------------

class DocumentChunker:
    """
    Deterministic document text chunker.
    Transforms raw document.extracted_text into semantically coherent,
    page-aware chunks with preserved source metadata.
    """

    PAGE_MARKER_REGEX = re.compile(r"^[ \t]*---\s*PAGE\s+(\d+)\s*---[ \t]*$", re.MULTILINE | re.IGNORECASE)

    def __init__(self, target_chunk_words: int = 50, max_chunk_words: int = 100, overlap_lines: int = 2):
        self.target_chunk_words = target_chunk_words
        self.max_chunk_words = max_chunk_words
        self.overlap_lines = overlap_lines

    def chunk_document(
        self,
        document_id: int,
        document_name: str,
        extracted_text: Optional[str],
        document_type: Optional[str] = None,
        reporting_period: Optional[str] = None,
        source_field: str = "extracted_text"
    ) -> List[RAGDocumentChunk]:
        """
        Split a document's extracted text into deterministic RAGDocumentChunks.
        Preserves page boundaries, section coherence, and source lineage.
        """
        if not extracted_text or not extracted_text.strip():
            return []

        clean_text = extracted_text.strip()
        pages = self._split_by_page(clean_text)

        chunks: List[RAGDocumentChunk] = []
        global_chunk_idx = 1

        for page_num, page_text in pages:
            page_chunks = self._chunk_page_text(
                document_id=document_id,
                document_name=document_name,
                page_text=page_text,
                page=page_num,
                document_type=document_type,
                reporting_period=reporting_period,
                source_field=source_field,
                start_index=global_chunk_idx
            )
            chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        return chunks

    def _split_by_page(self, text: str) -> List[Tuple[Optional[int], str]]:
        """
        Detect page markers such as '--- PAGE X ---' and segment text.
        If no page markers exist, returns a single segment with page=None.
        """
        matches = list(self.PAGE_MARKER_REGEX.finditer(text))
        if not matches:
            return [(None, text)]

        pages: List[Tuple[Optional[int], str]] = []
        for i, m in enumerate(matches):
            page_num = int(m.group(1))
            start_pos = m.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            page_content = text[start_pos:end_pos].strip()
            if page_content:
                pages.append((page_num, page_content))

        return pages if pages else [(None, text)]

    def _chunk_page_text(
        self,
        document_id: int,
        document_name: str,
        page_text: str,
        page: Optional[int],
        document_type: Optional[str],
        reporting_period: Optional[str],
        source_field: str,
        start_index: int
    ) -> List[RAGDocumentChunk]:
        """
        Break page content into bounded, semantically coherent chunks.
        Keeps tabular lines together and preserves text flow.
        """
        raw_lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        if not raw_lines:
            return []

        # Decompose any massive lines (> max_chunk_words) into sentence/clause lines
        lines: List[str] = []
        for l in raw_lines:
            words = l.split()
            if len(words) > self.max_chunk_words:
                # Split into sentence-like clauses
                sentences = re.split(r"(?<=[.!?])\s+", l)
                curr_sent = []
                for s in sentences:
                    curr_sent.append(s)
                    if sum(len(x.split()) for x in curr_sent) >= self.target_chunk_words:
                        lines.append(" ".join(curr_sent))
                        curr_sent = []
                if curr_sent:
                    lines.append(" ".join(curr_sent))
            else:
                lines.append(l)

        chunks: List[RAGDocumentChunk] = []
        curr_lines: List[str] = []
        curr_word_count = 0
        chunk_idx = start_index

        i = 0
        while i < len(lines):
            line = lines[i]
            words = len(line.split())
            curr_lines.append(line)
            curr_word_count += words
            i += 1

            # Check if we should avoid cutting right after a metric header label
            is_header_like = any(
                k in line.lower() for k in ["scope 1", "scope 2", "total ghg", "metric", "charges", "billing period", "description"]
            ) and len(line.split()) <= 5

            next_line = lines[i] if i < len(lines) else ""
            is_unit_line = next_line.lower().strip() in ["tco2e", "kwh", "kva", "liters", "pf", "inr", "ton", "kg", "%"]
            if is_unit_line:
                curr_lines.append(next_line)
                curr_word_count += len(next_line.split())
                i += 1

            if curr_word_count >= self.target_chunk_words and not is_header_like:
                chunk_str = "\n".join(curr_lines).strip()
                if chunk_str:
                    page_label = f"p{page}" if page is not None else "p0"
                    chunk_id = f"doc_{document_id}_{page_label}_c{chunk_idx}"
                    chunks.append(RAGDocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_name=document_name,
                        document_type=document_type,
                        page=page,
                        text=chunk_str,
                        reporting_period=reporting_period,
                        source_field=source_field
                    ))
                    chunk_idx += 1

                # Retain overlap if enabled
                if self.overlap_lines > 0 and len(curr_lines) > self.overlap_lines:
                    curr_lines = curr_lines[-self.overlap_lines:]
                    curr_word_count = sum(len(l.split()) for l in curr_lines)
                else:
                    curr_lines = []
                    curr_word_count = 0

        # Flush any remaining lines
        if curr_lines:
            chunk_str = "\n".join(curr_lines).strip()
            if chunk_str and (not chunks or chunk_str != chunks[-1].text):
                page_label = f"p{page}" if page is not None else "p0"
                chunk_id = f"doc_{document_id}_{page_label}_c{chunk_idx}"
                chunks.append(RAGDocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    document_type=document_type,
                    page=page,
                    text=chunk_str,
                    reporting_period=reporting_period,
                    source_field=source_field
                ))

        return chunks


# ---------------------------------------------------------------------------
# Lightweight Vector Representation & Index (Phase 8, 9, 10, 11, 12, 13)
# ---------------------------------------------------------------------------

class CopilotVectorIndex:
    """
    Lightweight, in-memory vector retrieval engine.
    Uses deterministic term-frequency and n-gram vectorization with cosine similarity.
    Requires no external vector databases, no remote network calls, and no API keys.
    """

    TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9_\-\.]{2,}\b")

    def __init__(self):
        self._chunks: Dict[str, RAGDocumentChunk] = {}
        self._chunk_tokens: Dict[str, List[str]] = {}
        self._vectors: Dict[str, Dict[str, float]] = {}
        self._df: Counter = Counter()
        self._idf: Dict[str, float] = {}

    def build_from_documents(self, documents: List[Any], chunker: Optional[DocumentChunker] = None) -> int:
        """
        Chunk and index a list of Document models or objects.
        Returns total number of chunks indexed.
        """
        self.clear()
        c = chunker or DocumentChunker()
        all_chunks: List[RAGDocumentChunk] = []

        for doc in documents:
            extracted = getattr(doc, "extracted_text", None)
            doc_id = getattr(doc, "id", 0)
            doc_name = getattr(doc, "original_filename", None) or getattr(doc, "filename", f"doc_{doc_id}")
            doc_type = getattr(doc, "document_type", None)
            period = getattr(doc, "reporting_period", None)

            # Check structured_data for period fallback if empty
            if not period and hasattr(doc, "structured_data") and isinstance(doc.structured_data, dict):
                period_data = doc.structured_data.get("period")
                if isinstance(period_data, dict):
                    period = period_data.get("billing_month") or period_data.get("end_date")

            doc_chunks = c.chunk_document(
                document_id=doc_id,
                document_name=doc_name,
                extracted_text=extracted,
                document_type=doc_type,
                reporting_period=period
            )
            all_chunks.extend(doc_chunks)

        self.add_chunks(all_chunks)
        return len(self._chunks)

    def add_document(self, doc: Any, chunker: Optional[DocumentChunker] = None) -> int:
        """Add or re-index a single Document."""
        doc_id = getattr(doc, "id", None)
        if doc_id is not None:
            self.remove_document(doc_id)

        c = chunker or DocumentChunker()
        extracted = getattr(doc, "extracted_text", None)
        doc_id = getattr(doc, "id", 0)
        doc_name = getattr(doc, "original_filename", None) or getattr(doc, "filename", f"doc_{doc_id}")
        doc_type = getattr(doc, "document_type", None)
        period = getattr(doc, "reporting_period", None)

        doc_chunks = c.chunk_document(
            document_id=doc_id,
            document_name=doc_name,
            extracted_text=extracted,
            document_type=doc_type,
            reporting_period=period
        )
        self.add_chunks(doc_chunks)
        return len(doc_chunks)

    def update_document(self, doc: Any, chunker: Optional[DocumentChunker] = None) -> int:
        """Update a document by replacing its chunks."""
        return self.add_document(doc, chunker=chunker)

    def remove_document(self, document_id: int) -> int:
        """Remove all chunks associated with a document_id."""
        to_remove = [cid for cid, chunk in self._chunks.items() if chunk.document_id == document_id]
        for cid in to_remove:
            del self._chunks[cid]
            if cid in self._chunk_tokens:
                del self._chunk_tokens[cid]
            if cid in self._vectors:
                del self._vectors[cid]

        self._recompute_idf_and_vectors()
        return len(to_remove)

    def add_chunks(self, chunks: List[RAGDocumentChunk]) -> None:
        """Add pre-constructed chunks and update vector representations."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._chunk_tokens[chunk.chunk_id] = self._tokenize(chunk.text)

        self._recompute_idf_and_vectors()

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[int] = None
    ) -> List[RAGChunkResult]:
        """
        Perform deterministic semantic similarity search over indexed chunks.
        Supports document-scoped filtering and handles zero-vectors safely.
        """
        if not self._chunks or not query or not query.strip():
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        q_vec = self._vectorize(q_tokens)
        results: List[RAGChunkResult] = []

        for cid, chunk in self._chunks.items():
            if document_id is not None and chunk.document_id != document_id:
                continue

            d_vec = self._vectors.get(cid, {})
            sim = self._cosine_similarity(q_vec, d_vec)

            results.append(RAGChunkResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                document_type=chunk.document_type,
                page=chunk.page,
                text=chunk.text,
                score=round(sim, 4),
                reporting_period=chunk.reporting_period,
                source_field=chunk.source_field
            ))

        # Deterministic sorting: highest score first, then document_id, then chunk_id
        results.sort(key=lambda r: (-r.score, r.document_id, r.chunk_id))
        return results[:top_k]

    def clear(self) -> None:
        """Clear all indexed chunks and vocabulary."""
        self._chunks.clear()
        self._chunk_tokens.clear()
        self._vectors.clear()
        self._df.clear()
        self._idf.clear()

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    # -----------------------------------------------------------------------
    # Internal Vector Math
    # -----------------------------------------------------------------------

    def _tokenize(self, text: str) -> List[str]:
        """Generate unigrams and bigrams from normalized text."""
        words = self.TOKEN_PATTERN.findall(text.lower())
        if not words:
            return []
        unigrams = words
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        return unigrams + bigrams

    def _recompute_idf_and_vectors(self) -> None:
        """Recompute IDF values across the corpus and unit-normalize chunk vectors."""
        self._df.clear()
        for tokens in self._chunk_tokens.values():
            for t in set(tokens):
                self._df[t] += 1

        n_docs = len(self._chunk_tokens)
        self._idf = {
            t: math.log((1.0 + n_docs) / (1.0 + freq)) + 1.0
            for t, freq in self._df.items()
        }

        self._vectors = {
            cid: self._vectorize(tokens)
            for cid, tokens in self._chunk_tokens.items()
        }

    def _vectorize(self, tokens: List[str]) -> Dict[str, float]:
        """Convert token list into an L2-normalized TF-IDF vector."""
        if not tokens:
            return {}

        tf = Counter(tokens)
        total_tokens = len(tokens)
        raw_vec: Dict[str, float] = {}

        for term, count in tf.items():
            idf_val = self._idf.get(term, 1.0)
            raw_vec[term] = (count / total_tokens) * idf_val

        norm = math.sqrt(sum(v * v for v in raw_vec.values()))
        if norm == 0.0:
            return {}

        return {term: val / norm for term, val in raw_vec.items()}

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Compute cosine similarity between two unit-normalized sparse vectors.
        Guarantees safe execution without NaN or ZeroDivisionError.
        """
        if not vec1 or not vec2:
            return 0.0

        # Choose smaller vector to iterate over
        small, large = (vec1, vec2) if len(vec1) < len(vec2) else (vec2, vec1)
        sim = sum(val * large.get(term, 0.0) for term, val in small.items())

        # Clamp between 0.0 and 1.0
        return max(0.0, min(1.0, float(sim)))


# Global singleton instance for convenient backend use
copilot_rag_chunker = DocumentChunker()
copilot_vector_index = CopilotVectorIndex()


def format_metric_label(key: Optional[str]) -> str:
    """Format metric_type key into clean human-readable title."""
    if not key:
        return "Metric"
    name_map = {
        "electricity_consumption": "Electricity Consumption",
        "renewable_energy": "Renewable Energy",
        "fuel_consumption": "Fuel Consumption",
        "peak_demand": "Peak Demand",
        "scope_1_emissions": "Scope 1 Emissions",
        "scope1_emissions": "Scope 1 Emissions",
        "scope_2_emissions": "Scope 2 Emissions",
        "scope2_emissions": "Scope 2 Emissions",
        "total_ghg_emissions": "Total GHG Emissions",
        "total_emissions": "Total GHG Emissions",
        "water_consumption": "Water Consumption",
        "recycled_water": "Recycled Water",
        "hazardous_waste": "Hazardous Waste",
        "non_hazardous_waste": "Non-Hazardous Waste",
        "recycled_waste": "Waste Recycled",
        "energy_cost": "Energy Cost",
    }
    return name_map.get(key, key.replace("_", " ").title())


class CopilotRAGRouter:
    """
    Lightweight deterministic query router (Phase 3).
    Determines retrieval modes (METRIC, DOCUMENT, HYBRID, EMISSIONS, RECOMMENDATION, ATTENTION, TREND, MISSING_DATA)
    without relying on the LLM.
    """

    @staticmethod
    def route_query(query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        q = (query or "").lower().strip()
        if not q:
            return "GENERAL"

        # 1. MISSING_DATA / REVIEW / ATTENTION
        if any(k in q for k in ["need review", "needs review", "attention", "pending review", "unverified", "flagged", "missing", "data gap", "gaps in data"]):
            if any(k in q for k in ["missing", "data gap", "unfilled", "not applicable"]):
                return "MISSING_DATA"
            return "ATTENTION"

        # 2. EMISSIONS REDUCTION / ACTION
        reduction_verbs = ["reduce", "reduction", "lower", "lowering", "decrease", "cut", "mitigate", "minimize"]
        emissions_terms = ["emission", "emissions", "carbon", "footprint", "ghg", "scope 1", "scope 2", "scope1", "scope2"]
        has_reduction = any(v in q for v in reduction_verbs) and any(e in q for e in emissions_terms)
        if has_reduction or any(k in q for k in ["how can i reduce", "how to reduce", "lower carbon footprint", "where should i focus to reduce"]):
            return "EMISSIONS"

        # 3. RECOMMENDATIONS / PRIORITY
        if any(k in q for k in ["focus on first", "focus first", "what should i focus", "biggest opportunity", "recommendation", "recommendations", "next steps", "action recommendation"]):
            return "RECOMMENDATION"

        # 4. TREND / HISTORICAL
        if any(k in q for k in ["why did", "trend", "change", "increase", "decrease", "history", "historical", "period over period", "trajectory"]):
            return "TREND"

        # 5. METRIC QUERY (numerical facts: peak demand, electricity consumption, fuel, water, waste, scope 1, scope 2, total ghg, cost)
        metric_keywords = ["peak demand", "electricity consumption", "fuel consumption", "water consumption", "scope 1", "scope 2", "total ghg", "active energy", "payable amount", "how much electricity", "how much fuel"]
        if any(k in q for k in metric_keywords) or (any(w in q for w in ["what is", "how much", "show", "tell me"]) and any(w in q for w in ["demand", "consumption", "emissions", "usage", "cost", "payable"])):
            return "METRIC"

        # 6. DOCUMENT QUERY (specific document text / solar / details)
        if any(k in q for k in ["document", "pdf", "bill say", "solar", "clause", "note", "certification", "compliance", "tariff", "summarize"]):
            return "DOCUMENT"

        return "HYBRID"


class CopilotHybridRetriever:
    """
    Hybrid Retriever (Phase 2, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15).
    Combines:
    1. Semantic document chunks (CopilotVectorIndex)
    2. Authoritative structured metrics (SustainabilityMetric with exact identity)
    3. Evidence lineage (SourceContext)
    4. Deterministic insights (MetricInsight)
    5. Deterministic recommendations (CopilotRecommendationService)
    6. Deterministic attention items (CopilotAttentionService)
    
    Operates strictly in READ-ONLY mode. Does NOT modify database state.
    """

    def __init__(self, vector_index: Optional[CopilotVectorIndex] = None):
        self.vector_index = vector_index or copilot_vector_index

    def retrieve(
        self,
        db: Session,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        document_id: Optional[int] = None
    ) -> RAGContext:
        """
        Build a strongly typed RAGContext for a query.
        Guarantees metric identity protection, source lineage, and strict document-scoped filtering.
        """
        clean_query = (query or "").strip()
        retrieval_mode = CopilotRAGRouter.route_query(clean_query, history=history)

        # 1. Sync / populate vector index with documents from DB if empty
        docs_query = db.query(Document).filter(Document.status == "COMPLETED")
        if document_id is not None:
            docs_query = docs_query.filter(Document.id == document_id)
        all_docs = docs_query.order_by(Document.id.desc()).all()

        if self.vector_index.total_chunks == 0 and all_docs:
            self.vector_index.build_from_documents(all_docs)

        # 2. Semantic Chunk Retrieval
        retrieved_chunks: List[RAGChunkResult] = []
        if retrieval_mode in ("DOCUMENT", "HYBRID", "EMISSIONS", "TREND", "RECOMMENDATION", "METRIC", "ATTENTION", "MISSING_DATA", "GENERAL"):
            retrieved_chunks = self.vector_index.search(clean_query, top_k=5, document_id=document_id)

        # 3. Authoritative Structured Metric Retrieval
        metrics_query = db.query(SustainabilityMetric, Document).join(
            Document, SustainabilityMetric.document_id == Document.id
        )
        if document_id is not None:
            metrics_query = metrics_query.filter(SustainabilityMetric.document_id == document_id)
        
        metrics_raw = metrics_query.order_by(SustainabilityMetric.id.desc()).all()

        rag_metrics: List[RAGMetric] = []
        seen_metric_keys = set()

        for m, doc in metrics_raw:
            m_key = (m.document_id, m.metric_type)
            if m_key in seen_metric_keys:
                continue

            is_relevant = self._is_metric_relevant(m, clean_query, retrieval_mode)
            if is_relevant:
                seen_metric_keys.add(m_key)
                rag_metrics.append(RAGMetric(
                    metric_id=m.id,
                    metric_name=format_metric_label(m.metric_type),
                    metric_type=m.metric_type,
                    category=m.category,
                    value=m.value,
                    unit=m.unit,
                    period=m.period_end or m.period_start or doc.reporting_period,
                    document_id=m.document_id,
                    document_name=doc.original_filename or doc.filename,
                    source_field=m.source_field,
                    source_text=m.source_text,
                    verification_status=m.verification_status,
                    confidence=m.confidence
                ))

        # Sort structured metrics by query relevance
        def score_rag_metric(rm: RAGMetric) -> int:
            score = 0
            m_type = rm.metric_type.lower()
            q_lower = clean_query.lower()
            m_parts = m_type.split("_")
            q_words = [w.strip("?,.!") for w in q_lower.split() if len(w.strip("?,.!")) > 2]
            score += sum(1 for w in q_words if any(w in part or part in w for part in m_parts))
            for kw in ["electricity", "fuel", "diesel", "water", "peak", "demand", "waste", "renewable", "solar", "emission", "scope"]:
                if kw in q_lower and kw in m_type:
                    score += 10
            return score

        rag_metrics.sort(key=score_rag_metric, reverse=True)

        # 4. Evidence Lineage (SourceContext)
        sources: List[SourceContext] = []
        seen_sources = set()

        for rm in rag_metrics:
            s_key = (rm.document_id, rm.source_field, rm.value)
            if s_key not in seen_sources:
                seen_sources.add(s_key)
                sources.append(SourceContext(
                    document_id=rm.document_id,
                    document_name=rm.document_name,
                    field=rm.source_field,
                    value=rm.value,
                    unit=rm.unit,
                    source_text=rm.source_text
                ))

        for chunk in retrieved_chunks:
            s_key = (chunk.document_id, chunk.source_field, chunk.chunk_id)
            if s_key not in seen_sources and len(sources) < 6:
                seen_sources.add(s_key)
                sources.append(SourceContext(
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    field=chunk.source_field,
                    value=None,
                    unit=None,
                    source_text=chunk.text[:200]
                ))

        # 5. Deterministic Insights Retrieval
        all_insights = insights_service.generate_metric_insights(db)
        if document_id is not None:
            all_insights = [i for i in all_insights if i.source_document_id == document_id]
        
        insights_ctx = [
            InsightContext(
                category=ins.category,
                severity=ins.severity,
                metric_type=ins.metric_type,
                message=ins.message,
                current_value=ins.current_value,
                previous_value=ins.previous_value,
                percentage_change=ins.percentage_change,
                source_document_id=ins.source_document_id
            ) for ins in all_insights[:5]
        ]

        # 6. Deterministic Recommendations Retrieval
        recs = copilot_recommendation_service.generate_recommendations(db, query=clean_query)
        if document_id is not None:
            recs = [r for r in recs if r.source_document_id == document_id]

        # 7. Deterministic Attention Items Retrieval
        att_res = copilot_attention_service.get_attention_items(db)
        att_items = att_res.items
        if document_id is not None:
            att_items = [a for a in att_items if a.document_id == document_id]

        # 8. Document Context & Review Items
        docs_ctx = [
            DocumentContext(
                document_id=d.id,
                filename=d.original_filename or d.filename,
                document_type=d.document_type,
                company_name=d.company_name,
                reporting_period=d.reporting_period,
                status=d.status,
                quality_score=float(d.quality_score or 0.0),
                verification_status=d.review_status or "READY"
            ) for d in all_docs[:5]
        ]

        review_docs = [d for d in all_docs if d.review_status == "NEEDS_REVIEW"]
        review_ctx = [
            ReviewContext(
                document_id=d.id,
                filename=d.original_filename or d.filename,
                reason=d.error_message or "Extraction fields unconfirmed",
                quality_score=float(d.quality_score or 0.0),
                affected_fields=[]
            ) for d in review_docs[:4]
        ]

        summary = CopilotSummary(
            document_count=len(all_docs),
            documents_needing_review=len(review_docs),
            verified_documents=len([d for d in all_docs if d.review_status == "VERIFIED"]),
            metric_count=len(metrics_raw),
            active_attention_items=len(att_items)
        )

        return RAGContext(
            query=clean_query,
            intent=retrieval_mode,
            retrieval_mode=retrieval_mode,
            document_id=document_id,
            chunks=retrieved_chunks,
            rag_metrics=rag_metrics,
            sources=sources,
            insights=insights_ctx,
            recommendations=recs,
            attention_items=att_items,
            review_items=review_ctx,
            documents=docs_ctx,
            summary=summary
        )

    def _is_metric_relevant(self, m: SustainabilityMetric, query: str, mode: str) -> bool:
        """Determine if a metric is relevant based on retrieval mode and query keywords."""
        if mode in ("EMISSIONS", "RECOMMENDATION"):
            return m.category == "carbon" or m.metric_type in (
                "scope_1_emissions", "scope_2_emissions", "total_ghg_emissions", "electricity_consumption"
            )
        if mode == "METRIC":
            q_lower = query.lower()
            q_words = [w.strip("?,.!") for w in q_lower.split() if len(w.strip("?,.!")) > 2]
            m_parts = m.metric_type.lower().split("_")
            word_match = any(w in part or part in w for w in q_words for part in m_parts)
            domain_kw = any(kw in q_lower and kw in m.metric_type.lower() for kw in [
                "electricity", "fuel", "diesel", "water", "peak", "demand", "waste", "renewable", "solar", "emission", "scope"
            ])
            return word_match or domain_kw
        return True


copilot_rag_router = CopilotRAGRouter()
copilot_hybrid_retriever = CopilotHybridRetriever()

