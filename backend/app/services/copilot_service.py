import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from backend.app.schemas.copilot import CopilotResponse
from backend.app.services.copilot_rag import copilot_hybrid_retriever
from backend.app.services.copilot_llm import copilot_llm_service

logger = logging.getLogger("senseible-copilot-service")

class CopilotService:
    """
    Senseible AI Copilot Service (Step 11R-3).
    Integrates Hybrid RAG retrieval (semantic chunks, authoritative structured metrics,
    evidence lineage, insights, recommendations, and attention alerts) with grounded LLM synthesis.
    """

    def __init__(self):
        self.is_initialized = True

    def chat(
        self,
        db: Session,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        document_id: Optional[int] = None
    ) -> CopilotResponse:
        """
        Process incoming user query, execute hybrid RAG retrieval across database and vector index,
        and generate a grounded, structured CopilotResponse.
        """
        logger.info(f"Copilot RAG chat query: {message[:60]}... (doc_id={document_id})")
        
        # 1. Execute Hybrid RAG Retrieval across database metrics, document chunks, evidence & insights
        rag_context = copilot_hybrid_retriever.retrieve(
            db,
            message,
            history=history,
            document_id=document_id
        )
        
        # 2. Generate grounded answer via CopilotLLMService (Live OpenAI or Deterministic Fallback)
        response = copilot_llm_service.generate_response(
            rag_context,
            history=history,
            recommendations=rag_context.recommendations,
            document_id=document_id
        )
        
        return response

copilot_service = CopilotService()
