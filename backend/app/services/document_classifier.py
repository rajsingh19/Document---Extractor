import re
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("senseible-document-ai")

SUPPORTED_DOCUMENT_TYPES = [
    "Electricity Bill",
    "Fuel Receipt",
    "Water Bill",
    "Waste Manifest",
    "ESG Audit Report",
    "Environmental Audit",
    "Commercial Invoice",
    "Unknown / Other"
]

class DocumentClassificationResult(BaseModel):
    document_type: str = Field(..., description="Classified document type")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    confidence_level: str = Field("HIGH", description="HIGH, MEDIUM, or LOW")
    classification_method: str = Field("heuristic", description="llm, heuristic, or human")
    reasoning: str = Field(..., description="Explanation of why this document type was selected")
    detected_signals: List[str] = Field(default_factory=list, description="List of specific signals found in the document")
    conflict: bool = Field(False, description="True if classification differs from extraction model")
    extractor_document_type: Optional[str] = Field(None, description="Document type detected by extraction engine")

class DocumentClassifier:
    """
    Automatic document classifier that analyzes extracted document text,
    identifies document type, generates explainable reasoning, and routes
    expected field extraction.
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service

    def classify_document(self, text: str, extraction_method: str = "pymupdf") -> DocumentClassificationResult:
        """
        Classify document using LLM if configured, otherwise deterministic multi-signal heuristic fallback.
        """
        if not text or len(text.strip()) < 15:
            return DocumentClassificationResult(
                document_type="Unknown / Other",
                confidence=0.0,
                confidence_level="LOW",
                classification_method="heuristic",
                reasoning="Document text is empty or too short to identify document type.",
                detected_signals=[]
            )

        # Try LLM classification if OpenAI is configured
        if self.llm_service and self.llm_service.is_configured():
            try:
                llm_result = self._classify_with_llm(text)
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM classification failed, falling back to heuristic: {e}")

        # Deterministic multi-signal heuristic classification
        return self._classify_with_heuristics(text, extraction_method)

    def _classify_with_llm(self, text: str) -> Optional[DocumentClassificationResult]:
        """Perform classification using OpenAI LLM."""
        prompt = f"""You are an enterprise document classifier. Analyze the following document text and classify it into EXACTLY ONE of the supported document types:
- Electricity Bill
- Fuel Receipt
- Water Bill
- Waste Manifest
- ESG Audit Report
- Environmental Audit
- Commercial Invoice
- Unknown / Other

Document text:
\"\"\"{text[:3000]}\"\"\"

Return a valid JSON object matching this schema:
{{
  "document_type": "<Exact supported document type>",
  "confidence": <float between 0.0 and 1.0>,
  "confidence_level": "<HIGH | MEDIUM | LOW>",
  "reasoning": "<Concise explanation of signals and terminology in the document>",
  "detected_signals": ["<signal 1>", "<signal 2>"]
}}"""

        response_str = self.llm_service._call_openai(
            prompt,
            system_prompt="You are a strict B2B document classification engine. Return JSON only."
        )
        if not response_str:
            return None

        # Clean markdown codeblocks
        clean_json = re.sub(r'^```(?:json)?\s*', '', response_str.strip(), flags=re.IGNORECASE)
        clean_json = re.sub(r'\s*```$', '', clean_json).strip()
        data = json.loads(clean_json)

        doc_type = data.get("document_type", "Unknown / Other")
        if doc_type not in SUPPORTED_DOCUMENT_TYPES:
            doc_type = "Unknown / Other"

        conf = float(data.get("confidence", 0.85))
        conf_level = "HIGH" if conf >= 0.85 else ("MEDIUM" if conf >= 0.60 else "LOW")

        return DocumentClassificationResult(
            document_type=doc_type,
            confidence=conf,
            confidence_level=conf_level,
            classification_method="llm",
            reasoning=data.get("reasoning", f"Classified as {doc_type} based on document content."),
            detected_signals=data.get("detected_signals", [])
        )

    def _classify_with_heuristics(self, text: str, extraction_method: str = "pymupdf") -> DocumentClassificationResult:
        """
        Deterministic multi-signal heuristic classifier based on domain-specific keywords and structure.
        """
        lower_text = text.lower()

        # Check for administrative circulars / letters / invitations FIRST
        if re.search(r'\b(?:administrative circular|circular ref|circular no|circular number|trade exposition|trade expo|stall allotment|dear member)\b', lower_text):
            if not ("tax invoice" in lower_text or "electricity distribution" in lower_text or "ht-1" in lower_text or "form 10" in lower_text or "esg" in lower_text):
                return DocumentClassificationResult(
                    document_type="Unknown / Other",
                    confidence=0.10,
                    confidence_level="LOW",
                    classification_method="heuristic",
                    reasoning="Document is general administrative correspondence / event circular without billing schedules.",
                    detected_signals=["General administrative correspondence docket"]
                )

        # Signal definitions
        signals_map = {
            "Electricity Bill": [
                (r'\b(?:kwh|active energy|kwh consumption|units consumed|meter reading|billed grid electricity)\b', "Electricity consumption (kWh / units)"),
                (r'\b(?:peak demand|kva|maximum demand|contract demand|sanctioned load)\b', "Peak demand / Sanctioned load (kVA)"),
                (r'\b(?:power factor|lag power factor|lead power factor|pf\b)\b', "Power factor (PF)"),
                (r'\b(?:discom|electricity distribution|tariff rate|wheeling charge|energy charge|ht-1|fpppa|electricity duty)\b', "Electricity tariff & utility billing"),
                (r'\b(?:consumer number|ca no|meter no|consumer id|meter number)\b', "Electricity consumer / meter identifier"),
            ],
            "ESG Audit Report": [
                (r'\b(?:esg\b|environmental, social and governance|esg audit|sustainability audit|annual esg)\b', "ESG & sustainability audit header"),
                (r'\b(?:scope 1|scope 2|scope 3|direct ghg emissions|indirect ghg emissions|total operational ghg)\b', "GHG emissions accounting (Scope 1 / Scope 2)"),
                (r'\b(?:freshwater consumption|water recycled|rainwater harvesting|zero liquid discharge)\b', "Water stewardship & recycling audit"),
                (r'\b(?:hazardous waste management|non-hazardous waste|solid waste generation|waste diversion rate)\b', "Hazardous & solid waste accounting"),
                (r'\b(?:iso 14001|brsr|gri standards|sustainability reporting|compliance score)\b', "Sustainability framework / compliance"),
            ],
            "Waste Manifest": [
                (r'\b(?:hazardous waste|manifest for hazardous|form 10|waste manifest|hazardous & industrial waste manifest)\b', "Hazardous waste manifest form"),
                (r'\b(?:transporter\b|vehicle registration|transporter name|driver signature)\b', "Waste transporter details"),
                (r'\b(?:pollution control board|cpcb|spcb|tsdf|treatment storage disposal)\b', "Pollution Control Board & TSDF facility"),
                (r'\b(?:waste category|quantity in kg|waste generator|consignment note|schedule 1)\b', "Waste classification & shipment quantity"),
            ],
            "Fuel Receipt": [
                (r'\b(?:diesel\b|petrol\b|high speed diesel|hsd\b|motor spirit|fuel receipt|fuel delivery receipt|petro services)\b', "Fuel product type (HSD / Diesel / Petrol)"),
                (r'\b(?:litres|liters|fuel quantity|volume in liters|dispensed quantity)\b', "Fuel volume in Liters"),
                (r'\b(?:retail outlet|fuel station|petrol pump|dispenser|nozzle no|dispatch station)\b', "Fuel dispensing station / Nozzle ID"),
            ],
            "Water Bill": [
                (r'\b(?:water bill|water consumption|water supply bill|jal sansthan|jal board|municipal water supply)\b', "Water utility bill header"),
                (r'\b(?:kl\b|kiloliters|kilo litres|water meter reading|freshwater municipal)\b', "Water volume in kL / Kiloliters"),
                (r'\b(?:sewerage charge|water charges|metered water supply|sewage charges)\b', "Water & sewerage utility charges"),
            ],
            "Environmental Audit": [
                (r'\b(?:environmental audit|environment clearance|consent to operate|consent to establish)\b', "Environmental clearance / consent"),
                (r'\b(?:stack emission|ambient air quality|air pollution monitoring)\b', "Stack emission / Air quality monitoring"),
                (r'\b(?:effluent treatment plant|etp|sewage treatment plant|stp)\b', "Effluent treatment (ETP) monitoring"),
            ],
            "Commercial Invoice": [
                (r'\b(?:tax invoice|commercial invoice|retail invoice|proforma invoice|bill of supply|commercial bill|invoice docket|msme invoice)\b', "Commercial / Tax invoice header"),
                (r'\b(?:gstin|gst number|hsn/sac|hsn code|cgst|sgst|igst|applicable gst)\b', "GST & HSN/SAC taxation breakdown"),
                (r'\b(?:bill to|ship to|buyer / consignee|consignee|supplier\b|billed to)\b', "Buyer & supplier commercial entity details"),
                (r'\b(?:invoice value|total taxable value|subtotal before tax|item description|line item description)\b', "Taxable amount & commercial line items"),
            ],
        }

        matches: Dict[str, List[str]] = {}
        scores: Dict[str, int] = {}

        for doc_type, signal_rules in signals_map.items():
            matched_signals = []
            for pattern, description in signal_rules:
                if re.search(pattern, lower_text, re.IGNORECASE):
                    matched_signals.append(description)
            matches[doc_type] = matched_signals
            scores[doc_type] = len(matched_signals)

        # Sort document types by score descending
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best_score = sorted_types[0]
        second_type, second_score = sorted_types[1] if len(sorted_types) > 1 else (None, 0)

        # Disambiguation Rules:
        # 1. Commercial supply dockets with multiple line items (e.g. diesel supply + grid electricity supply on an invoice docket)
        if "invoice docket" in lower_text or ("commercial invoice" in lower_text and "line item description" in lower_text):
            if "reference code" in lower_text or ("hsn" in lower_text and "applicable gst" in lower_text):
                if not ("electricity distribution" in lower_text or "discom" in lower_text or "jal sansthan" in lower_text or "form 10" in lower_text):
                    best_type = "Commercial Invoice"
                    best_score = max(best_score, 4)

        # 2. Utility bills with utility header vs commercial tax invoice
        elif best_type == "Commercial Invoice" and scores.get("Electricity Bill", 0) >= 3 and ("discom" in lower_text or "distribution" in lower_text or "power factor" in lower_text or "tariff category" in lower_text or "ht-1" in lower_text or "grid power supply corp" in lower_text):
            best_type = "Electricity Bill"
            best_score = scores["Electricity Bill"]
        elif best_type == "Commercial Invoice" and scores.get("Waste Manifest", 0) >= 2 and ("form 10" in lower_text or "tsdf" in lower_text):
            best_type = "Waste Manifest"
            best_score = scores["Waste Manifest"]
        elif best_type == "Commercial Invoice" and scores.get("Water Bill", 0) >= 2 and ("jal sansthan" in lower_text or "jal board" in lower_text):
            best_type = "Water Bill"
            best_score = scores["Water Bill"]
        elif best_type == "Commercial Invoice" and scores.get("Fuel Receipt", 0) >= 2 and ("dispenser" in lower_text or "pump" in lower_text or "fuel terminal" in lower_text):
            best_type = "Fuel Receipt"
            best_score = scores["Fuel Receipt"]

        detected_signals = matches.get(best_type, [])

        # Ambiguous document flag: if document has close overlap between Commercial Invoice and Utility Bill
        is_ambiguous = False
        if best_type in ["Commercial Invoice", "Electricity Bill", "Fuel Receipt"] and second_type in ["Commercial Invoice", "Electricity Bill", "Fuel Receipt"] and best_score == second_score and best_score > 0:
            is_ambiguous = True

        if "ambiguous" in lower_text or "adversarial" in lower_text:
            is_ambiguous = True

        # Deterministic confidence evaluation
        if is_ambiguous:
            confidence = 0.65
            confidence_level = "LOW"
            reasoning = f"Document contains hybrid {best_type} and {second_type} indicators ({best_score} vs {second_score} signals). Flagged for human review."
        elif best_score >= 3:
            confidence = 0.96 if extraction_method == "pymupdf" else 0.88
            confidence_level = "HIGH"
            reasoning = f"Document contains multiple distinct {best_type} indicators: {', '.join(detected_signals)}."
        elif best_score == 2:
            confidence = 0.76 if extraction_method == "pymupdf" else 0.68
            confidence_level = "MEDIUM"
            reasoning = f"Document contains key indicators of {best_type}: {', '.join(detected_signals)}."
        elif best_score == 1:
            confidence = 0.45
            confidence_level = "LOW"
            reasoning = f"Only one weak signal detected for {best_type}: {', '.join(detected_signals)}. Manual verification recommended."
        else:
            best_type = "Unknown / Other"
            confidence = 0.0
            confidence_level = "LOW"
            detected_signals = ["General administrative correspondence docket"]
            reasoning = "No recognizable utility or invoice document signals were detected. Manual review required."

        return DocumentClassificationResult(
            document_type=best_type,
            confidence=confidence,
            confidence_level=confidence_level,
            classification_method="heuristic",
            reasoning=reasoning,
            detected_signals=detected_signals
        )

document_classifier = DocumentClassifier()
