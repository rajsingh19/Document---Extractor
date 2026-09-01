import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from backend.app.schemas.copilot import CopilotResponse
from backend.app.services.copilot_context import copilot_context_service
from backend.app.services.copilot_llm import copilot_llm_service

logger = logging.getLogger("senseible-copilot-service")

class CopilotService:
    """
    Senseible AI Copilot Service (Step 11C).
    Integrates intent routing, grounded database context retrieval,
    and LLM / deterministic grounded Q&A answering.
    """

    def __init__(self):
        self.is_initialized = True

    def chat(
        self,
        db: Session,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> CopilotResponse:
        """
        Process incoming user query, classify intent, build grounded context,
        and generate a grounded factual response with verified source citations.
        """
        logger.info(f"Copilot received message query: {message[:60]}...")
        
        # 1. Build grounded context from database
        context = copilot_context_service.build_context(db, message, history=history)
        
        # 2. Generate grounded answer via CopilotLLMService (Live OpenAI or Deterministic Grounding)
        response = copilot_llm_service.generate_response(context, history=history)
        
        return response

copilot_service = CopilotService()
