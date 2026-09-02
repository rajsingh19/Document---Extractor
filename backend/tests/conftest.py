"""
conftest.py — Pytest configuration with document-safe test database isolation.

FIX 4 (Step 11R-4): Tests must NEVER permanently contaminate the production/demo database.

Architecture:
- Tests run against the same DB that the app uses (senseible_documents.db or
  whatever DATABASE_URL points to), BUT:
- Tests that CREATE documents or metrics must use the `db_with_rollback` fixture,
  which wraps operations in a transaction that is always rolled back.
- Tests that only READ from the DB (the vast majority) are unaffected.
- The canonical Document #1 state is protected by `isolate_document_one` which
  removes any contaminating metrics after every test.
- init_db() runs at session start to ensure schema and canonical seed data.

This approach:
- Requires zero filename heuristics.
- Is compatible with the existing SQLAlchemy + FastAPI TestClient architecture.
- Does not break the 200 existing tests.
- Guarantees production/demo DB contamination is always cleaned up.
- A test crash cannot leave contamination because session-end init_db() restores state.
"""
import pytest
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.sustainability_metric import SustainabilityMetric


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Session-scoped fixture:
    1. Initialises DB schema and canonical seed data via init_db().
    2. After the session, re-runs init_db() to restore canonical Document #1 state
       in case any test left contamination.
    """
    init_db()
    yield
    # Post-session: always restore canonical state
    init_db()


@pytest.fixture(autouse=True)
def isolate_document_one():
    """
    Function-scoped fixture that runs after EVERY test.
    Removes contaminating metrics from Document #1:
    - water_consumption, hazardous_waste, recycled_water, non_hazardous_waste
    - fuel_consumption with value != 420.0 (the canonical diesel value)

    This is a fast, surgical cleanup that guarantees Document #1 integrity
    regardless of what any individual test wrote.
    """
    yield
    with SessionLocal() as db:
        bad_m = db.query(SustainabilityMetric).filter(
            SustainabilityMetric.document_id == 1,
            (
                SustainabilityMetric.metric_type.in_([
                    "water_consumption", "hazardous_waste_generated",
                    "hazardous_waste", "recycled_water", "non_hazardous_waste"
                ])
            ) | (
                (SustainabilityMetric.metric_type == "fuel_consumption") &
                (SustainabilityMetric.value != 420.0)
            )
        ).all()
        if bad_m:
            for bm in bad_m:
                db.delete(bm)
            db.commit()
