"""
services/reduction_project.py — Carbon Reduction Project Tracking & Audit Trail Service (Step 16).

Manages user-initiated reduction projects linked to opportunities, baseline references, and audit event logs.
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.reduction_project import ReductionProject, ReductionProjectEvent
from backend.app.models.reduction_opportunity import ReductionOpportunity
from backend.app.schemas.reduction_project import (
    ReductionProjectCreate,
    ReductionProjectUpdate,
)

logger = logging.getLogger("senseible-reduction-project-service")


class ReductionProjectService:
    """
    Service for creating and managing reduction projects with event auditing.
    """

    def _generate_project_code(self, category: str, db: Session) -> str:
        cat_prefix = (category or "GEN").upper()[:4]
        year_str = datetime.utcnow().strftime("%Y")
        count = db.query(ReductionProject).count() + 1
        return f"PRJ-{cat_prefix}-{year_str}-{count:04d}"

    def create_project(self, db: Session, data: ReductionProjectCreate) -> ReductionProject:
        """
        Create a new ReductionProject and record CREATED event.
        """
        code = self._generate_project_code(data.category, db)

        project = ReductionProject(
            project_code=code,
            title=data.title,
            description=data.description,
            category=data.category.upper(),
            scope=data.scope.upper() if data.scope else None,
            opportunity_id=data.opportunity_id,
            activity_type=data.activity_type,
            status="PLANNED",
            owner=data.owner,
            start_date=data.start_date,
            target_date=data.target_date,
            baseline_period=data.baseline_period,
            baseline_co2e=Decimal(str(data.baseline_co2e)) if data.baseline_co2e is not None else None,
            baseline_co2e_unit=data.baseline_co2e_unit or "kgCO2e",
            target_description=data.target_description,
            notes=data.notes,
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Log creation event
        event = ReductionProjectEvent(
            project_id=project.id,
            event_type="CREATED",
            previous_status=None,
            new_status="PLANNED",
            note=f"Project '{project.title}' created with status PLANNED.",
        )
        db.add(event)

        # If linked to an opportunity, update opportunity status to IN_PROGRESS
        if data.opportunity_id:
            opp = db.query(ReductionOpportunity).filter_by(id=data.opportunity_id).first()
            if opp and opp.status in ["OPEN", "ACKNOWLEDGED"]:
                opp.status = "IN_PROGRESS"

        db.commit()
        db.refresh(project)
        return project

    def create_project_from_opportunity(
        self,
        db: Session,
        opportunity_id: int,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> ReductionProject:
        """
        Create project directly from an identified ReductionOpportunity with prepopulated evidence & baseline reference.
        """
        opp = db.query(ReductionOpportunity).filter_by(id=opportunity_id).first()
        if not opp:
            raise ValueError(f"ReductionOpportunity with ID {opportunity_id} not found.")

        custom = custom_data or {}

        title = custom.get("title") or f"Project: {opp.title}"
        description = custom.get("description") or opp.description
        owner = custom.get("owner")
        target_description = custom.get("target_description") or opp.recommended_action

        create_dto = ReductionProjectCreate(
            title=title,
            description=description,
            category=opp.category,
            scope=opp.scope,
            opportunity_id=opp.id,
            activity_type=opp.activity_type,
            owner=owner,
            baseline_period=custom.get("baseline_period"),
            baseline_co2e=float(opp.calculated_co2e) if opp.calculated_co2e is not None else None,
            baseline_co2e_unit=opp.calculated_co2e_unit or "kgCO2e",
            target_description=target_description,
            notes=custom.get("notes") or f"Originating Opportunity: {opp.opportunity_code}",
        )

        return self.create_project(db, create_dto)

    def get_projects(
        self,
        db: Session,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        status: Optional[str] = None,
        opportunity_id: Optional[int] = None,
    ) -> List[ReductionProject]:
        """
        List and filter reduction projects.
        """
        query = db.query(ReductionProject)
        if category:
            query = query.filter(ReductionProject.category == category.strip().upper())
        if scope:
            query = query.filter(ReductionProject.scope == scope.strip().upper())
        if status:
            query = query.filter(ReductionProject.status == status.strip().upper())
        if opportunity_id is not None:
            query = query.filter(ReductionProject.opportunity_id == opportunity_id)

        return query.order_by(desc(ReductionProject.created_at)).all()

    def get_project(self, db: Session, project_id: int) -> Optional[ReductionProject]:
        return db.query(ReductionProject).filter_by(id=project_id).first()

    def update_project(
        self,
        db: Session,
        project_id: int,
        data: ReductionProjectUpdate,
    ) -> Optional[ReductionProject]:
        """
        Update project details and record audit event if status or target changes.
        """
        project = self.get_project(db, project_id)
        if not project:
            return None

        status_changed = False
        prev_status = project.status

        if data.title is not None:
            project.title = data.title
        if data.description is not None:
            project.description = data.description
        if data.category is not None:
            project.category = data.category.upper()
        if data.scope is not None:
            project.scope = data.scope.upper()
        if data.owner is not None:
            project.owner = data.owner
        if data.start_date is not None:
            project.start_date = data.start_date
        if data.target_date is not None:
            project.target_date = data.target_date
        if data.baseline_period is not None:
            project.baseline_period = data.baseline_period
        if data.baseline_co2e is not None:
            project.baseline_co2e = Decimal(str(data.baseline_co2e))
        if data.baseline_co2e_unit is not None:
            project.baseline_co2e_unit = data.baseline_co2e_unit
        if data.target_description is not None:
            project.target_description = data.target_description
        if data.actual_post_project_co2e is not None:
            project.actual_post_project_co2e = Decimal(str(data.actual_post_project_co2e))
        if data.actual_post_project_unit is not None:
            project.actual_post_project_unit = data.actual_post_project_unit
        if data.notes is not None:
            project.notes = data.notes

        if data.status is not None and data.status.upper() != prev_status:
            valid_statuses = {"PLANNED", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"}
            st = data.status.upper()
            if st not in valid_statuses:
                raise ValueError(f"Invalid project status '{data.status}'. Must be one of {valid_statuses}")
            project.status = st
            status_changed = True

        db.commit()

        if status_changed:
            event = ReductionProjectEvent(
                project_id=project.id,
                event_type="STATUS_CHANGE",
                previous_status=prev_status,
                new_status=project.status,
                note=f"Status changed from {prev_status} to {project.status}.",
            )
            db.add(event)
            db.commit()

        db.refresh(project)
        return project

    def update_status(
        self,
        db: Session,
        project_id: int,
        new_status: str,
        note: Optional[str] = None,
    ) -> Optional[ReductionProject]:
        """
        Dedicated status transition with event logging.
        """
        valid_statuses = {"PLANNED", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"}
        st = new_status.strip().upper()
        if st not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        project = self.get_project(db, project_id)
        if not project:
            return None

        prev_status = project.status
        project.status = st

        event = ReductionProjectEvent(
            project_id=project.id,
            event_type="STATUS_CHANGE",
            previous_status=prev_status,
            new_status=st,
            note=note or f"Status changed from {prev_status} to {st}.",
        )
        db.add(event)

        # If project completed or cancelled, optionally update linked opportunity
        if st == "COMPLETED" and project.opportunity_id:
            opp = db.query(ReductionOpportunity).filter_by(id=project.opportunity_id).first()
            if opp:
                opp.status = "COMPLETED"

        db.commit()
        db.refresh(project)
        return project

    def get_project_events(self, db: Session, project_id: int) -> List[ReductionProjectEvent]:
        """
        Retrieve chronological audit trail events for a reduction project.
        """
        return db.query(ReductionProjectEvent).filter_by(
            project_id=project_id
        ).order_by(ReductionProjectEvent.created_at.asc()).all()


reduction_project_service = ReductionProjectService()
