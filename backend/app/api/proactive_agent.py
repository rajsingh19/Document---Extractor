"""
api/proactive_agent.py — REST Controller for Proactive AI Sustainability Agent (Step 23 & Improvement Patches).

Exposes idempotent execution, daily brief retrieval, action queue management,
audit event inspection, and structured non-hallucinating explanations.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database.session import get_db
from backend.app.models.proactive_agent import AgentAction, AgentActionEvent
from backend.app.schemas.proactive_agent import (
    AgentActionResponse,
    AgentActionListResponse,
    AgentActionUpdate,
    AgentActionEventResponse,
    AgentActionEventListResponse,
    AgentBriefResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentStatusResponse,
    AgentExplanationResponse,
)
from backend.app.services.proactive_agent import proactive_agent_service, AGENT_VERSION

router = APIRouter(prefix="/agent", tags=["AI Sustainability Agent"])


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    payload: Optional[AgentRunRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Idempotently runs the Proactive AI Sustainability Agent decision engine.
    Running twice with identical data produces 0 duplicate actions.
    """
    doc_id = payload.document_id if payload else None
    force_recalc = payload.force_recalculate if payload else False

    try:
        result = proactive_agent_service.evaluate_actions(
            db=db,
            document_id=doc_id,
            force_recalculate=force_recalc
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent evaluation failed: {str(e)}"
        )


@router.get("/brief", response_model=AgentBriefResponse)
def get_sustainability_brief(
    document_id: Optional[int] = Query(None, description="Optional document ID scoping"),
    db: Session = Depends(get_db)
):
    """
    Returns the authoritative AI Sustainability Brief (Patch 4 & Patch 8).
    Strictly separates Actuals, Forecasts (FORECAST — NOT ACTUAL), and Scenarios (SCENARIO — NOT ACTUAL).
    """
    try:
        brief = proactive_agent_service.get_sustainability_brief(db=db, document_id=document_id)
        return brief
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI Sustainability Brief: {str(e)}"
        )


@router.get("/status", response_model=AgentStatusResponse)
def get_agent_status(
    db: Session = Depends(get_db)
):
    """
    Returns high-level agent runtime status, last evaluated timestamp, and queue counts.
    """
    total = db.query(AgentAction).count()
    open_cnt = db.query(AgentAction).filter(AgentAction.status == "OPEN").count()
    in_prog = db.query(AgentAction).filter(AgentAction.status == "IN_PROGRESS").count()
    completed = db.query(AgentAction).filter(AgentAction.status == "COMPLETED").count()
    red_cnt = db.query(AgentAction).filter(
        AgentAction.queue_type == "REDUCTION",
        AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
    ).count()
    dq_cnt = db.query(AgentAction).filter(
        AgentAction.queue_type == "DATA_QUALITY",
        AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
    ).count()
    ready_cnt = db.query(AgentAction).filter(
        AgentAction.dependency_status == "READY",
        AgentAction.status.in_(["OPEN", "IN_PROGRESS"])
    ).count()

    return {
        "agent_version": AGENT_VERSION,
        "engine_version": AGENT_VERSION,
        "last_evaluated": proactive_agent_service.get_last_evaluated(),
        "total_actions": total,
        "open_actions": open_cnt,
        "in_progress_actions": in_prog,
        "completed_actions": completed,
        "active_actions_count": open_cnt + in_prog,
        "reduction_queue_count": red_cnt,
        "data_quality_queue_count": dq_cnt,
        "ready_actions_count": ready_cnt,
    }


@router.get("/actions", response_model=AgentActionListResponse)
def list_actions(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    category_filter: Optional[str] = Query(None, alias="category"),
    queue: Optional[str] = Query(None),
    queue_type: Optional[str] = Query(None),
    action_queue: Optional[str] = Query(None),
    dependency_status: Optional[str] = Query(None),
    document_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Lists persisted AgentActions with filtering across queue_type, status, priority, and document scope.
    """
    query = db.query(AgentAction)

    if status_filter:
        query = query.filter(AgentAction.status == status_filter.upper())
    if priority_filter:
        query = query.filter(AgentAction.priority == priority_filter.upper())
    if category_filter:
        query = query.filter(AgentAction.category == category_filter.upper())
    q_filter = queue or queue_type or action_queue
    if q_filter:
        query = query.filter(AgentAction.queue_type == q_filter.upper())
    if dependency_status:
        query = query.filter(AgentAction.dependency_status == dependency_status.upper())
    if document_id:
        query = query.filter(AgentAction.document_id == document_id)

    # Deterministic ordering by priority_score descending
    query = query.order_by(desc(AgentAction.priority_score), desc(AgentAction.created_at))

    total = query.count()
    actions = query.limit(limit).all()

    # Aggregate counts
    base_q = db.query(AgentAction)
    if document_id:
        base_q = base_q.filter(AgentAction.document_id == document_id)

    open_c = base_q.filter(AgentAction.status == "OPEN").count()
    inp_c = base_q.filter(AgentAction.status == "IN_PROGRESS").count()
    comp_c = base_q.filter(AgentAction.status == "COMPLETED").count()
    dism_c = base_q.filter(AgentAction.status == "DISMISSED").count()
    red_c = base_q.filter(AgentAction.queue_type == "REDUCTION", AgentAction.status.in_(["OPEN", "IN_PROGRESS"])).count()
    dq_c = base_q.filter(AgentAction.queue_type == "DATA_QUALITY", AgentAction.status.in_(["OPEN", "IN_PROGRESS"])).count()

    return {
        "actions": [a.to_dict() for a in actions],
        "total": total,
        "open_count": open_c,
        "in_progress_count": inp_c,
        "completed_count": comp_c,
        "dismissed_count": dism_c,
        "reduction_count": red_c,
        "data_quality_count": dq_c,
    }


@router.get("/actions/{action_id}", response_model=AgentActionResponse)
def get_action(
    action_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed AgentAction by ID with full provenance lineage and dependency references.
    """
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentAction #{action_id} not found.")
    return action.to_dict()


@router.patch("/actions/{action_id}", response_model=AgentActionResponse)
def patch_action(
    action_id: int,
    payload: AgentActionUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates action metadata (e.g. due context or next step).
    """
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentAction #{action_id} not found.")

    if payload.due_context is not None:
        action.due_context = payload.due_context
    if payload.recommended_action is not None:
        action.recommended_action = payload.recommended_action
    if payload.next_step is not None:
        action.next_step = payload.next_step
    if payload.status is not None:
        action.status = payload.status.upper()

    action.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(action)
    return action.to_dict()


@router.post("/actions/{action_id}/start", response_model=AgentActionResponse)
def start_action(
    action_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Transitions action to IN_PROGRESS and records audit event.
    """
    try:
        action = proactive_agent_service.start_action(
            db=db, action_id=action_id, actor_type="USER", reason=reason
        )
        return action.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/actions/{action_id}/complete", response_model=AgentActionResponse)
def complete_action(
    action_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Transitions action to COMPLETED, records audit event, and activates dependent child actions from BLOCKED to READY (Patch 3).
    """
    try:
        action = proactive_agent_service.complete_action(
            db=db, action_id=action_id, actor_type="USER", reason=reason
        )
        return action.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/actions/{action_id}/dismiss", response_model=AgentActionResponse)
def dismiss_action(
    action_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Transitions action to DISMISSED and records audit event.
    """
    try:
        action = proactive_agent_service.dismiss_action(
            db=db, action_id=action_id, actor_type="USER", reason=reason
        )
        return action.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/actions/{action_id}/events", response_model=AgentActionEventListResponse)
def list_action_events(
    action_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns audit trail of all lifecycle transitions for an action.
    """
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentAction #{action_id} not found.")

    events = db.query(AgentActionEvent).filter(
        AgentActionEvent.action_id == action_id
    ).order_by(AgentActionEvent.created_at.asc()).all()

    return {
        "events": [e.to_dict() for e in events],
        "total": len(events),
    }


@router.post("/explain/{action_id}", response_model=AgentExplanationResponse)
def explain_action(
    action_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns structured explanation contract: WHAT, WHY, NEXT, EVIDENCE, FOLLOW_UP, LIMITATION (Patch 5).
    """
    try:
        explanation = proactive_agent_service.explain_action(db=db, action_id=action_id)
        return explanation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
