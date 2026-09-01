import logging
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.schemas.copilot import CopilotResponse
from backend.app.services.copilot_context import copilot_context_service

logger = logging.getLogger("senseible-copilot-service")

class CopilotService:
    """
    Senseible AI Copilot Service (Step 11B).
    Integrates the grounded context layer with intent routing and factual source retrieval.
    LLM reasoning and dynamic generation will be introduced in Step 11C.
    """

    def __init__(self):
        self.is_initialized = True

    def chat(self, db: Session, message: str) -> CopilotResponse:
        """
        Process incoming user query, classify intent, build grounded context,
        and return a structured response with verified sources and summary.
        """
        logger.info(f"Copilot received message query: {message[:60]}...")
        
        # Build grounded context from database
        context = copilot_context_service.build_context(db, message)
        
        # Generate appropriate follow-up actions based on intent
        actions = []
        if context.intent == "DOCUMENT_REVIEW":
            actions = ["Review unverified documents", "Verify extracted parameters"]
        elif context.intent == "EMISSIONS_ANALYSIS":
            actions = ["Inspect Scope 1 & 2 carbon footprint", "View emissions period change"]
        elif context.intent == "TREND_ANALYSIS":
            actions = ["View historical metric trends", "Check period-over-period delta"]
        elif context.intent == "METRIC_QUERY":
            actions = ["Check latest normalized metrics", "View source bill excerpt"]
        elif context.intent == "MISSING_DATA":
            actions = ["Upload missing reporting period bill", "Review expected fields"]
        else:
            actions = ["Review verified sustainability metrics", "Check documents needing attention"]

        # Step 11B grounded response text with intent verification
        answer = (
            f"Grounded context retrieved for intent: {context.intent}. "
            f"Found {len(context.documents)} relevant document(s), "
            f"{len(context.metrics)} metric(s), and {len(context.sources)} verifiable source excerpt(s)."
        )

        return CopilotResponse(
            answer=answer,
            intent=context.intent,
            sources=context.sources,
            actions=actions,
            context_available=True,
            summary=context.summary
        )

copilot_service = CopilotService()
