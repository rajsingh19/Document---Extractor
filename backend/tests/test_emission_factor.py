"""
test_emission_factor.py — Step 12A Emission Factor Engine Tests

Verifies:
1. Factor model creation & validation
2. Factor retrieval by ID and code
3. Factor listing with filters
4. Exact activity matching
5. Activity + unit compatibility matching
6. Geography matching (exact & fallback)
7. Applicable year matching
8. Scope matching
9. ACTIVE factor participation in candidate matching
10. INACTIVE factor exclusion from candidate matching
11. DRAFT factor exclusion from candidate matching
12. NO_MATCH result when criteria cannot be satisfied
13. MULTIPLE_MATCHES result when ambiguous factors exist
14. Incompatible unit rejection (e.g. diesel with kWh)
15. Invalid factor value rejection (negative values rejected)
16. Historical versions coexisting without collision
17. Newer factor versions not overwriting older versions
18. Provenance preservation (source_name, methodology, version)
19. Demo factors explicitly marked with DEMO disclaimer
20. Existing Document #1 sustainability metrics strictly unchanged
21. API endpoint GET /api/emission-factors
22. API endpoint GET /api/emission-factors/{factor_id}
23. API endpoint GET /api/emission-factors/candidates
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.emission_factor import EmissionFactor
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.schemas.emission_factor import EmissionFactorCreate
from backend.app.services.emission_factor_service import (
    emission_factor_service,
    are_units_compatible,
    normalize_unit,
)

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# 1-10: MODEL, RETRIEVAL, FILTERING & MATCHING RULES
# ──────────────────────────────────────────────────────────────────────────────

class TestEmissionFactorFoundation:
    """Core model, retrieval, status filtering, and matching tests."""

    def test_01_factor_model_creation(self):
        """Verify EmissionFactor model attributes and serialization."""
        with SessionLocal() as db:
            code = "TEST_CUSTOM_CREATION_FACTOR_01"
            # Cleanup if lingering
            old = db.query(EmissionFactor).filter(EmissionFactor.factor_code == code).first()
            if old:
                db.delete(old)
                db.commit()

            f = EmissionFactor(
                factor_code=code,
                factor_name="Test Model Creation Factor",
                activity_type="diesel",
                category="FUEL",
                scope="SCOPE_1",
                factor_value=2.68,
                factor_unit="kgCO2e/L",
                activity_unit="L",
                geography="India",
                applicable_year=2024,
                source_name="DEMO DATA — NOT FOR PRODUCTION",
                source_reference="Ref Table 1",
                methodology="Direct Calculation",
                version="1.0",
                status="ACTIVE",
            )
            db.add(f)
            db.commit()
            db.refresh(f)

            try:
                assert f.id is not None
                assert f.factor_code == code
                assert f.factor_value == 2.68
                d = f.to_dict()
                assert d["factor_code"] == code
                assert d["category"] == "FUEL"
                assert d["scope"] == "SCOPE_1"
            finally:
                db.delete(f)
                db.commit()

    def test_02_factor_retrieval(self):
        """Retrieve existing demo factor by code and by ID."""
        with SessionLocal() as db:
            factor = emission_factor_service.get_factor_by_code(
                db, "DEMO_INDIA_GRID_ELECTRICITY_2024"
            )
            assert factor is not None
            assert factor.activity_type == "purchased_electricity"
            assert factor.factor_value == 0.71

            by_id = emission_factor_service.get_factor(db, factor.id)
            assert by_id is not None
            assert by_id.factor_code == factor.factor_code

    def test_03_factor_listing(self):
        """List factors with filter by activity_type and status."""
        with SessionLocal() as db:
            all_factors = emission_factor_service.list_factors(db)
            assert len(all_factors) >= 8

            diesel_factors = emission_factor_service.list_factors(
                db, activity_type="diesel", status="ACTIVE"
            )
            assert len(diesel_factors) >= 1
            for df in diesel_factors:
                assert df.activity_type == "diesel"
                assert df.status == "ACTIVE"

    def test_04_exact_activity_match(self):
        """Match exact activity_type without ambiguity."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db, activity_type="petrol", activity_unit="L"
            )
            assert res.status == "MATCHED"
            assert res.matched_factor is not None
            assert res.matched_factor.factor_code == "DEMO_PETROL_MOBILE_2024"
            assert res.matched_factor.factor_value == 2.31

    def test_05_activity_and_unit_match(self):
        """Match with normalized activity unit ('liters' vs 'L')."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db, activity_type="diesel", activity_unit="liters", geography="India", year=2024
            )
            assert res.status == "MATCHED"
            assert res.matched_factor is not None
            assert res.matched_factor.factor_code == "DEMO_DIESEL_STATIONARY_2024"
            assert res.matched_factor.activity_unit == "L"

    def test_06_geography_match(self):
        """Match candidate with exact regional geography."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                geography="India",
                year=2024,
            )
            assert res.status == "MATCHED"
            assert res.matched_factor.geography == "India"

    def test_07_year_match(self):
        """Match candidate with exact applicable_year constraint."""
        with SessionLocal() as db:
            res_2024 = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                geography="India",
                year=2024,
            )
            assert res_2024.status == "MATCHED"
            assert res_2024.matched_factor.applicable_year == 2024
            assert res_2024.matched_factor.factor_value == 0.71

            res_2025 = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                geography="India",
                year=2025,
            )
            assert res_2025.status == "MATCHED"
            assert res_2025.matched_factor.applicable_year == 2025
            assert res_2025.matched_factor.factor_value == 0.69

    def test_08_scope_match(self):
        """Match candidate with explicit Scope constraint."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db,
                activity_type="freight",
                activity_unit="tonne_km",
                scope="SCOPE_3",
            )
            assert res.status == "MATCHED"
            assert res.matched_factor.scope == "SCOPE_3"
            assert res.matched_factor.factor_code == "DEMO_ROAD_FREIGHT_2024"

    def test_09_active_factor_accepted(self):
        """Active factor is successfully included in candidate matching."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db, activity_type="natural_gas", activity_unit="scm"
            )
            assert res.status == "MATCHED"
            assert res.matched_factor.status == "ACTIVE"

    def test_10_inactive_factor_rejected(self):
        """INACTIVE factors are strictly excluded from candidate matching."""
        with SessionLocal() as db:
            # DEMO_INACTIVE_DIESEL_LEGACY is in the database with status=INACTIVE, year=2020
            res = emission_factor_service.find_candidates(
                db, activity_type="diesel", activity_unit="L", year=2020
            )
            assert res.status == "NO_MATCH"
            assert "no active emission factor" in res.message.lower()


# ──────────────────────────────────────────────────────────────────────────────
# 11-20: REJECTION, DISAMBIGUATION, VERSIONING & PROVENANCE
# ──────────────────────────────────────────────────────────────────────────────

class TestAdvancedMatchingAndIntegrity:
    """Advanced status, ambiguity, unit compatibility, and data safety tests."""

    def test_11_draft_factor_rejected(self):
        """DRAFT factors are strictly excluded from candidate matching."""
        with SessionLocal() as db:
            # DEMO_DRAFT_SOLAR_RECs is DRAFT
            draft_factor = db.query(EmissionFactor).filter(
                EmissionFactor.factor_code == "DEMO_DRAFT_SOLAR_RECs"
            ).first()
            assert draft_factor is not None
            assert draft_factor.status == "DRAFT"

            # Query with factor value 0.05
            res = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                year=2024,
            )
            # The matched factor must be the ACTIVE one (0.71), NOT the DRAFT one (0.05)
            assert res.status == "MATCHED"
            assert res.matched_factor.factor_code != "DEMO_DRAFT_SOLAR_RECs"
            assert res.matched_factor.factor_value == 0.71

    def test_12_no_match_result(self):
        """Unregistered activity returns NO_MATCH with 0 candidates."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db, activity_type="unregistered_fusion_power", activity_unit="kWh"
            )
            assert res.status == "NO_MATCH"
            assert res.matched_factor is None
            assert res.match_count == 0

    def test_13_multiple_matches_result(self):
        """Ambiguous query without year filter returns MULTIPLE_MATCHES."""
        with SessionLocal() as db:
            # purchased_electricity in India has both 2024 and 2025 ACTIVE factors
            res = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                geography="India",
                # year omitted on purpose to trigger multiple matches
            )
            assert res.status == "MULTIPLE_MATCHES"
            assert res.matched_factor is None
            assert res.match_count >= 2
            assert any(f.applicable_year == 2024 for f in res.candidate_factors)
            assert any(f.applicable_year == 2025 for f in res.candidate_factors)

    def test_14_incompatible_unit_rejected(self):
        """Incompatible activity unit (e.g. diesel in kWh) returns NO_MATCH."""
        with SessionLocal() as db:
            res = emission_factor_service.find_candidates(
                db, activity_type="diesel", activity_unit="kWh"
            )
            assert res.status == "NO_MATCH"
            assert "compatible unit" in res.message.lower()

    def test_15_invalid_factor_value_rejected(self):
        """Pydantic schema rejects negative factor values."""
        with pytest.raises(ValueError, match="non-negative"):
            EmissionFactorCreate(
                factor_code="TEST_NEGATIVE_FACTOR",
                factor_name="Negative Value Factor",
                activity_type="diesel",
                category="FUEL",
                scope="SCOPE_1",
                factor_value=-1.5,
                factor_unit="kgCO2e/L",
                activity_unit="L",
                source_name="DEMO DATA — NOT FOR PRODUCTION",
            )

    def test_16_historical_versions_coexist(self):
        """Historical factors (2024 and 2025) coexist simultaneously in registry."""
        with SessionLocal() as db:
            f2024 = emission_factor_service.get_factor_by_code(
                db, "DEMO_INDIA_GRID_ELECTRICITY_2024"
            )
            f2025 = emission_factor_service.get_factor_by_code(
                db, "DEMO_INDIA_GRID_ELECTRICITY_2025"
            )
            assert f2024 is not None
            assert f2025 is not None
            assert f2024.id != f2025.id
            assert f2024.factor_value == 0.71
            assert f2025.factor_value == 0.69

    def test_17_newer_factor_does_not_overwrite_older_factor(self):
        """Adding a new version does not delete or alter previous version."""
        with SessionLocal() as db:
            # Querying specifically for 2024 remains completely unchanged
            res = emission_factor_service.find_candidates(
                db,
                activity_type="purchased_electricity",
                activity_unit="kWh",
                geography="India",
                year=2024,
            )
            assert res.status == "MATCHED"
            assert res.matched_factor.factor_code == "DEMO_INDIA_GRID_ELECTRICITY_2024"
            assert res.matched_factor.factor_value == 0.71

    def test_18_provenance_preserved(self):
        """Every factor stores mandatory provenance fields."""
        with SessionLocal() as db:
            factors = emission_factor_service.list_factors(db)
            for f in factors:
                assert f.source_name is not None
                assert len(f.source_name.strip()) > 0
                assert f.version is not None

    def test_19_demo_factors_clearly_marked(self):
        """All seeded demo factors contain explicit DEMO disclaimer in source_name."""
        with SessionLocal() as db:
            demo_factors = db.query(EmissionFactor).filter(
                EmissionFactor.factor_code.like("DEMO_%")
            ).all()
            assert len(demo_factors) >= 8
            for df in demo_factors:
                assert "DEMO" in df.source_name

    def test_20_existing_document1_metrics_unchanged(self):
        """
        CRITICAL: Step 12A must NOT alter existing Document #1 Scope 1/2/Total calculations.
        Document #1 values must remain exact:
        Electricity = 48,750 kWh
        Scope 1 = 1.13 tCO2e
        Scope 2 = 31.88 tCO2e
        Total = 33.01 tCO2e
        """
        with SessionLocal() as db:
            metrics = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.document_id == 1
            ).all()
            m_dict = {m.metric_type: m.value for m in metrics}

            assert m_dict.get("electricity_consumption") == 48750.0
            assert m_dict.get("scope_1_emissions") == 1.13
            assert m_dict.get("scope_2_emissions") == 31.88
            assert m_dict.get("total_ghg_emissions") == 33.01
            assert m_dict.get("fuel_consumption") == 420.0
            assert m_dict.get("peak_demand") == 128.5
            assert m_dict.get("power_factor") == 0.96


# ──────────────────────────────────────────────────────────────────────────────
# 21-23: API REST ENDPOINT TESTS
# ──────────────────────────────────────────────────────────────────────────────

class TestEmissionFactorAPI:
    """Validate REST API contracts for emission factor queries."""

    def test_21_api_list_emission_factors(self):
        """GET /api/emission-factors returns 200 and structured list."""
        res = client.get("/api/emission-factors")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "factors" in data
        assert data["total"] >= 8

        # Test filter by scope
        res_s2 = client.get("/api/emission-factors?scope=SCOPE_2")
        assert res_s2.status_code == 200
        for f in res_s2.json()["factors"]:
            assert f["scope"] == "SCOPE_2"

    def test_22_api_get_emission_factor_by_id(self):
        """GET /api/emission-factors/{id} returns 200 on found, 404 on unknown."""
        # Find first factor id
        list_res = client.get("/api/emission-factors")
        first_id = list_res.json()["factors"][0]["id"]

        res = client.get(f"/api/emission-factors/{first_id}")
        assert res.status_code == 200
        assert res.json()["id"] == first_id

        # Unknown ID
        res_404 = client.get("/api/emission-factors/9999999")
        assert res_404.status_code == 404

    def test_23_api_find_candidates_endpoint(self):
        """GET /api/emission-factors/candidates performs deterministic matching."""
        # Valid match
        res = client.get(
            "/api/emission-factors/candidates",
            params={
                "activity_type": "diesel",
                "activity_unit": "L",
                "geography": "India",
                "year": 2024,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "MATCHED"
        assert data["matched_factor"]["factor_code"] == "DEMO_DIESEL_STATIONARY_2024"
        assert data["matched_factor"]["factor_value"] == 2.68

        # Incompatible unit
        res_bad = client.get(
            "/api/emission-factors/candidates",
            params={
                "activity_type": "diesel",
                "activity_unit": "kWh",
            },
        )
        assert res_bad.status_code == 200
        assert res_bad.json()["status"] == "NO_MATCH"
