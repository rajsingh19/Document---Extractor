import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from backend.app.schemas.copilot import CopilotResponse
from backend.app.services.copilot_context import copilot_context_service
from backend.app.services.copilot_llm import copilot_llm_service
from backend.app.services.copilot_recommendations import copilot_recommendation_service

logger = logging.getLogger("senseible-copilot-service")

class CopilotService:
    """
    Senseible AI Copilot Service (Step 11E).
    Integrates intent routing, grounded database context retrieval,
    actionable sustainability recommendations, and LLM / deterministic grounded Q&A.
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
        Process incoming user query, classify intent, build grounded context,
        generate deterministic recommendations, and return structured grounded response.
        """
        logger.info(f"Copilot received message query: {message[:60]}... (doc_id={document_id})")
        
        # 1. Build grounded context from database
        context = copilot_context_service.build_context(db, message, history=history, document_id=document_id)
        
        # 2. Generate deterministic recommendation candidates if relevant to actions/sustainability
        recommendations = copilot_recommendation_service.generate_recommendations(db, message)
        if document_id is not None:
            recommendations = [r for r in recommendations if r.source_document_id == document_id]
        
        # 3. Generate grounded answer via CopilotLLMService (Live OpenAI or Deterministic Grounding)
        response = copilot_llm_service.generate_response(
            context,
            history=history,
            recommendations=recommendations,
            document_id=document_id
        )
        
        return response

copilot_service = CopilotService()
