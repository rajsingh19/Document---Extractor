"""
api/reduction_roadmap.py — FastAPI Endpoints for Personalized Reduction Roadmap Engine (Step 22B).

Provides REST endpoints for creating target-driven reduction roadmaps, regenerating phased actions,
updating progress/status, and retrieving immutable audit events.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.reduction_roadmap import (
    RoadmapCreateRequest,
    RoadmapUpdateRequest,
    RoadmapItemStatusUpdateRequest,
    RoadmapItemResponse,
    RoadmapEventResponse,
    ReductionRoadmapResponse,
    ReductionRoadmapDetail,
    RoadmapProgressResponse,
    RoadmapListResponse,
)
from backend.app.services.reduction_roadmap import ReductionRoadmapService

router = APIRouter(prefix="/reduction-roadmaps", tags=["Reduction Roadmap Engine"])
service = ReductionRoadmapService()


@router.post(
    "",
    response_model=ReductionRoadmapDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new personalized reduction roadmap from target",
)
def create_reduction_roadmap(
    payload: RoadmapCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Initializes a new ReductionRoadmap, determines the accounting baseline from POSTED ledger entries,
    calculates deterministic target emissions & gap, and generates 4-phase structured action items.
    """
    try:
        roadmap = service.create_roadmap(
            db=db,
            target_reduction_percent=payload.target_reduction_percent,
            name=payload.name,
            document_id=payload.document_id,
            reporting_year=payload.reporting_year,
            baseline_period=payload.baseline_period,
            target_year=payload.target_year,
            target_period=payload.target_period,
        )
        return roadmap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reduction roadmap: {str(e)}",
        )


@router.get(
    "",
    response_model=RoadmapListResponse,
    summary="List all reduction roadmaps with optional filters",
)
def list_reduction_roadmaps(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, ACTIVE, ON_TRACK, etc.)"),
    db: Session = Depends(get_db),
):
    """
    Returns all reduction roadmaps matching the specified filters.
    """
    roadmaps = service.list_roadmaps(db=db, document_id=document_id, status=status)
    return RoadmapListResponse(
        total=len(roadmaps),
        items=[ReductionRoadmapResponse.model_validate(r) for r in roadmaps],
    )


@router.get(
    "/{id}",
    response_model=ReductionRoadmapDetail,
    summary="Get full reduction roadmap detail including items and events",
)
def get_reduction_roadmap_detail(
    id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieves full details of a specific reduction roadmap.
    """
    roadmap = service.get_roadmap(db=db, roadmap_id=id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reduction roadmap #{id} not found",
        )
    return roadmap


@router.post(
    "/{id}/generate",
    response_model=ReductionRoadmapDetail,
    summary="Regenerate phased action items for a roadmap",
)
def regenerate_roadmap_items(
    id: int,
    db: Session = Depends(get_db),
):
    """
    Regenerates all action items deterministically from latest Step 22A priorities and projects.
    """
    try:
        roadmap = service.generate_roadmap_items(db=db, roadmap_id=id)
        return roadmap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate roadmap items: {str(e)}",
        )


@router.get(
    "/{id}/progress",
    response_model=RoadmapProgressResponse,
    summary="Get progress tracking (Roadmap Progress vs Emissions Progress)",
)
def get_roadmap_progress(
    id: int,
    db: Session = Depends(get_db),
):
    """
    Returns progress analytics clearly distinguishing actions completed from actual carbon ledger changes.
    """
    try:
        progress = service.calculate_progress(db=db, roadmap_id=id)
        return progress
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{id}",
    response_model=ReductionRoadmapResponse,
    summary="Update roadmap status or metadata",
)
def update_reduction_roadmap(
    id: int,
    payload: RoadmapUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates roadmap metadata, target year/period, or lifecycle status.
    """
    try:
        updated = service.update_roadmap(
            db=db,
            roadmap_id=id,
            name=payload.name,
            status=payload.status,
            confidence=payload.confidence,
            target_year=payload.target_year,
            target_period=payload.target_period,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{id}/items/{item_id}",
    response_model=RoadmapItemResponse,
    summary="Update execution status of an individual roadmap item",
)
def update_roadmap_item_status(
    id: int,
    item_id: int,
    payload: RoadmapItemStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Updates the status (NOT_STARTED, IN_PROGRESS, BLOCKED, COMPLETED, CANCELLED) of an action item.
    """
    try:
        item = service.update_item_status(
            db=db,
            roadmap_id=id,
            item_id=item_id,
            new_status=payload.status,
            notes=payload.notes,
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{id}/events",
    response_model=List[RoadmapEventResponse],
    summary="Get audit event history for a roadmap",
)
def get_roadmap_events(
    id: int,
    db: Session = Depends(get_db),
):
    """
    Returns the immutable audit log of status transitions and milestones for this roadmap.
    """
    events = service.get_roadmap_events(db=db, roadmap_id=id)
    return events
