"""
api/reduction_intelligence.py — FastAPI Endpoints for Reduction Opportunity Intelligence Engine (Step 22A).

CRITICAL BOUNDARIES:
- Provides deterministic decision-support for carbon reduction focus.
- Never accepts hallucinated savings, reduction percentages, or ROI.
- Does NOT mutate accounting ledger entries, calculations, or metrics.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.reduction_intelligence import (
    ReductionPriorityResponse,
    ReductionPriorityDetail,
    ReductionPriorityList,
    ReductionIntelligenceSummary,
    RecalculateResponse,
)
from backend.app.services.reduction_intelligence import reduction_intelligence_service

router = APIRouter(prefix="/reduction-intelligence", tags=["Reduction Opportunity Intelligence"])


@router.get("", response_model=ReductionPriorityList)
def list_reduction_priorities(
    document_id: Optional[int] = Query(None, description="Filter by Document ID"),
    scope: Optional[str] = Query(None, description="Filter by Scope: SCOPE_1, SCOPE_2, SCOPE_3, or ALL"),
    priority_level: Optional[str] = Query(None, description="Filter by Priority Level: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL"),
    category: Optional[str] = Query(None, description="Filter by Category: ENERGY, FUEL, TRANSPORT, WATER, WASTE, DATA_QUALITY"),
    db: Session = Depends(get_db),
):
    """
    Get ranked reduction priorities based on POSTED ledger entries, historical trends,
    Step 21 forecasts, opportunities, and projects.
    """
    priorities = reduction_intelligence_service.get_priorities(
        db=db,
        document_id=document_id,
        scope=scope,
        priority_level=priority_level,
        category=category,
    )
    items = [ReductionPriorityResponse(**p.to_dict()) for p in priorities]
    return ReductionPriorityList(total=len(items), items=items)


@router.get("/priorities", response_model=ReductionPriorityList)
def get_ranked_priorities(
    document_id: Optional[int] = Query(None, description="Filter by Document ID"),
    scope: Optional[str] = Query(None, description="Filter by Scope"),
    priority_level: Optional[str] = Query(None, description="Filter by Priority Level"),
    category: Optional[str] = Query(None, description="Filter by Category"),
    db: Session = Depends(get_db),
):
    """
    Alias endpoint for ranked reduction priorities.
    """
    return list_reduction_priorities(
        document_id=document_id,
        scope=scope,
        priority_level=priority_level,
        category=category,
        db=db,
    )


@router.get("/summary", response_model=ReductionIntelligenceSummary)
def get_reduction_intelligence_summary(
    document_id: Optional[int] = Query(None, description="Filter summary by Document ID"),
    db: Session = Depends(get_db),
):
    """
    Get executive summary KPI counters and top reduction focus areas.
    """
    return reduction_intelligence_service.get_summary(db=db, document_id=document_id)


@router.get("/document/{document_id}", response_model=ReductionPriorityList)
def get_document_reduction_priorities(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Get reduction priorities specifically scoped to a single document.
    """
    priorities = reduction_intelligence_service.get_priorities(
        db=db,
        document_id=document_id,
    )
    items = [ReductionPriorityResponse(**p.to_dict()) for p in priorities]
    return ReductionPriorityList(total=len(items), items=items)


@router.post("/recalculate", response_model=RecalculateResponse)
def recalculate_reduction_priorities(
    document_id: Optional[int] = Query(None, description="Recalculate for specific document or global"),
    db: Session = Depends(get_db),
):
    """
    Trigger deterministic re-evaluation of reduction priorities from source ledger and opportunities.
    Does not mutate underlying ledger entries, calculations, or metrics.
    """
    priorities = reduction_intelligence_service.evaluate_priorities(
        db=db,
        document_id=document_id,
        save_to_db=True,
    )
    return RecalculateResponse(
        status="SUCCESS",
        message=f"Successfully re-evaluated {len(priorities)} reduction priorities.",
        priorities_generated=len(priorities),
        version=reduction_intelligence_service.version,
    )


@router.get("/recalculate", response_model=RecalculateResponse)
def recalculate_reduction_priorities_get(
    document_id: Optional[int] = Query(None, description="Recalculate for specific document or global"),
    db: Session = Depends(get_db),
):
    """
    GET convenience endpoint for deterministic re-evaluation.
    """
    return recalculate_reduction_priorities(document_id=document_id, db=db)


@router.get("/{priority_id}", response_model=ReductionPriorityDetail)
def get_reduction_priority_detail(
    priority_id: int,
    db: Session = Depends(get_db),
):
    """
    Get full detail for a single reduction priority including transparent score breakdown and audit lineage.
    """
    priority = reduction_intelligence_service.get_priority_by_id(db=db, priority_id=priority_id)
    if not priority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reduction priority with id {priority_id} not found."
        )

    # Calculate summary total posted emissions for percentage
    summary = reduction_intelligence_service.get_summary(db=db, document_id=priority.document_id)
    
    p_dict = priority.to_dict()
    detail = ReductionPriorityDetail(
        **p_dict,
        percentage_of_total=None,
        trend_description=f"{priority.change_percent:+.1f}% change" if priority.change_percent is not None else "Stable / Single Period",
        forecast_status=f"Projected {priority.forecast_emissions_kgco2e / 1000.0:.4f} tCO2e" if priority.forecast_emissions_kgco2e else "Unavailable (insufficient historical data)",
        existing_project_status=f"Project #{priority.project_id}" if priority.project_id else "No active project",
        is_data_quality_issue=(priority.data_quality_score > 0 or priority.blocker_score > 0),
        action_type="CONCRETE" if (priority.opportunity_id and not (priority.data_quality_score > 0)) else ("DATA_GAP" if priority.data_quality_score > 0 else "ANALYSIS_REQUIRED"),
        limitations="Statistical decision-support score based on recorded POSTED ledger entries and historical actuals. Does not guarantee operational savings.",
        score_breakdown={
            "impact": {"score": float(priority.impact_score), "max": 30.0, "description": "Materiality share of total posted emissions"},
            "trend": {"score": float(priority.trend_score), "max": 20.0, "description": "Period-over-period increase and multi-period persistence"},
            "forecast": {"score": float(priority.forecast_score), "max": 15.0, "description": "Step 21 predictive emissions trajectory"},
            "persistence": {"score": float(priority.persistence_score), "max": 15.0, "description": "Consistency across distinct actual reporting periods"},
            "actionability": {"score": float(priority.actionability_score), "max": 10.0, "description": "Presence of concrete operational opportunity"},
            "data_quality": {"score": float(priority.data_quality_score), "max": 5.0, "description": "Emission factor or measurement confidence issue"},
            "blocker": {"score": float(priority.blocker_score), "max": 5.0, "description": "Material blocker requiring resolution"},
            "total_score": float(priority.priority_score),
            "priority_level": priority.priority_level,
        }
    )
    return detail
