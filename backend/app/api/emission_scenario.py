"""
api/emission_scenario.py — REST Controller for Emissions Scenario / What-If Engine (Step 22C).

Exposes endpoints for creating, recalculating, listing, and inspecting hypothetical
decarbonization scenarios without modifying historical accounting ledgers.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.emission_scenario import (
    ScenarioCreateRequest,
    ScenarioUpdateRequest,
    EmissionScenarioDetailResponse,
    EmissionScenarioListResponse,
    ScenarioResultResponse,
)
from backend.app.services.emission_scenario import EmissionScenarioService

router = APIRouter(prefix="/emission-scenarios", tags=["Emission Scenarios"])
service = EmissionScenarioService()


@router.post("", response_model=EmissionScenarioDetailResponse, status_code=status.HTTP_201_CREATED)
def create_emission_scenario(
    payload: ScenarioCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Creates and calculates a new hypothetical what-if scenario.
    """
    try:
        scenario = service.create_and_calculate_scenario(db=db, payload=payload)
        return scenario
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create scenario: {str(e)}")


@router.get("", response_model=EmissionScenarioListResponse)
def list_emission_scenarios(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, CALCULATED, ARCHIVED)"),
    db: Session = Depends(get_db)
):
    """
    Lists all non-archived scenarios (or filtered by status).
    """
    items = service.list_scenarios(db=db, document_id=document_id, status=status)
    return EmissionScenarioListResponse(total=len(items), items=items)


@router.get("/document/{document_id}", response_model=EmissionScenarioListResponse)
def list_document_scenarios(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Convenience endpoint to list scenarios scoped to a specific document.
    """
    items = service.list_scenarios(db=db, document_id=document_id)
    return EmissionScenarioListResponse(total=len(items), items=items)


@router.get("/{scenario_id}", response_model=EmissionScenarioDetailResponse)
def get_emission_scenario(
    scenario_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves full details of a specific scenario, including inputs and source-level results.
    """
    scenario = service.get_scenario_by_id(db=db, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scenario with id {scenario_id} not found")
    return scenario


@router.post("/{scenario_id}/calculate", response_model=EmissionScenarioDetailResponse)
def recalculate_emission_scenario(
    scenario_id: int,
    db: Session = Depends(get_db)
):
    """
    Recalculates an existing scenario against current baseline ledger actuals.
    """
    try:
        scenario = service.recalculate_scenario(db=db, scenario_id=scenario_id)
        return scenario
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to recalculate scenario: {str(e)}")


@router.get("/{scenario_id}/results", response_model=List[ScenarioResultResponse])
def get_scenario_results(
    scenario_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns source-level calculation results with factor snapshots.
    """
    scenario = service.get_scenario_by_id(db=db, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scenario with id {scenario_id} not found")
    return scenario.results


@router.patch("/{scenario_id}", response_model=EmissionScenarioDetailResponse)
def update_emission_scenario(
    scenario_id: int,
    payload: ScenarioUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates scenario metadata (name, description, status).
    """
    scenario = service.update_scenario(db=db, scenario_id=scenario_id, payload=payload)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scenario with id {scenario_id} not found")
    return scenario


@router.delete("/{scenario_id}", status_code=status.HTTP_200_OK)
def delete_or_archive_scenario(
    scenario_id: int,
    hard_delete: bool = Query(False, description="Whether to permanently delete instead of archive"),
    db: Session = Depends(get_db)
):
    """
    Archives a scenario (or permanently deletes if hard_delete=True).
    """
    success = service.delete_scenario(db=db, scenario_id=scenario_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scenario with id {scenario_id} not found")
    return {"message": "Scenario archived successfully" if not hard_delete else "Scenario deleted permanently"}
