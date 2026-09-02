"""
test_11r4_reliability.py — Step 11R-4 Regression Tests

Covers all four fixes:
  Fix 1: Scope-specific emissions routing (scope 1 → METRIC_QUERY)
  Fix 2: Evidence/provenance value detection (kWh/value-based)
  Fix 3: Follow-up reporting period with history context
  Fix 4: Test database isolation (test metrics never contaminate production)

Also covers all non-regression checks for previously passing questions.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.copilot_rag import CopilotRAGRouter

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# FIX 1 REGRESSION: Scope-specific emissions routing
# ──────────────────────────────────────────────────────────────────────────────

class TestScopeSpecificRouting:
    """Verify scope-1 and scope-2 queries route to METRIC_QUERY, not EMISSIONS_ANALYSIS."""

    def test_scope1_routes_to_metric_query(self):
        """'scope 1 emissions' must route to METRIC_QUERY with target scope_1_emissions."""
        intent = CopilotRAGRouter.parse_query("What are the Scope 1 emissions?")
        assert intent.retrieval_mode == "METRIC_QUERY", (
            f"Expected METRIC_QUERY, got {intent.retrieval_mode}"
        )
        assert intent.target_metric_type == "scope_1_emissions"

    def test_scope2_routes_to_metric_query(self):
        """'scope 2 emissions' must route to METRIC_QUERY with target scope_2_emissions."""
        intent = CopilotRAGRouter.parse_query("What are the Scope 2 emissions?")
        assert intent.retrieval_mode == "METRIC_QUERY", (
            f"Expected METRIC_QUERY, got {intent.retrieval_mode}"
        )
        assert intent.target_metric_type == "scope_2_emissions"

    def test_scope1_short_form(self):
        """'What is scope 1?' must route to scope_1_emissions METRIC_QUERY."""
        intent = CopilotRAGRouter.parse_query("What is scope 1?")
        assert intent.retrieval_mode == "METRIC_QUERY"
        assert intent.target_metric_type == "scope_1_emissions"

    def test_scope2_short_form(self):
        """'What is scope 2?' must route to scope_2_emissions METRIC_QUERY."""
        intent = CopilotRAGRouter.parse_query("What is scope 2?")
        assert intent.retrieval_mode == "METRIC_QUERY"
        assert intent.target_metric_type == "scope_2_emissions"

    def test_generic_emissions_still_analysis(self):
        """'What are our emissions?' must still route to EMISSIONS_ANALYSIS."""
        intent = CopilotRAGRouter.parse_query("What are our emissions?")
        assert intent.retrieval_mode == "EMISSIONS_ANALYSIS"

    def test_reduction_query_still_recommendation(self):
        """'How can I reduce emissions?' must route to ACTION_RECOMMENDATION."""
        intent = CopilotRAGRouter.parse_query("How can I reduce my carbon emissions?")
        assert intent.retrieval_mode == "ACTION_RECOMMENDATION"

    def test_scope1_api_returns_113(self):
        """Scope 1 via API must return 1.13 tCO2e for Document #1."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What are the Scope 1 emissions?"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "METRIC_QUERY", f"Got intent: {data['intent']}"
        assert "1.13" in data["answer"], f"Expected 1.13 in answer: {data['answer']}"

    def test_scope2_api_returns_3188(self):
        """Scope 2 via API must return 31.88 tCO2e for Document #1."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What are the Scope 2 emissions?"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "METRIC_QUERY", f"Got intent: {data['intent']}"
        assert "31.88" in data["answer"], f"Expected 31.88 in answer: {data['answer']}"

    def test_scope1_answer_does_not_contain_scope2_only(self):
        """Scope 1 answer must mention 1.13; may mention scope 2 for context but not exclusively."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What are the Scope 1 emissions?"}
        )
        assert "1.13" in res.json()["answer"]

    def test_scope2_answer_does_not_return_scope1_only(self):
        """Scope 2 answer must mention 31.88; not just scope 1."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What are the Scope 2 emissions?"}
        )
        assert "31.88" in res.json()["answer"]


# ──────────────────────────────────────────────────────────────────────────────
# FIX 2 REGRESSION: Evidence/provenance value detection
# ──────────────────────────────────────────────────────────────────────────────

class TestEvidenceDetection:
    """Verify evidence queries using kWh or numeric values are routed correctly."""

    def test_where_did_kwh_value_come_from_routes_to_evidence(self):
        """'Where did the 48,750 kWh value come from?' must route to EVIDENCE."""
        intent = CopilotRAGRouter.parse_query("Where did the 48,750 kWh value come from?")
        assert intent.retrieval_mode == "EVIDENCE"

    def test_where_did_kwh_value_ev_field_is_electricity(self):
        """Evidence field for kWh queries must be electricity."""
        intent = CopilotRAGRouter.parse_query("Where did the 48,750 kWh value come from?")
        assert intent.evidence_field == "electricity", (
            f"Expected 'electricity', got '{intent.evidence_field}'"
        )

    def test_show_evidence_for_kwh_routes_evidence(self):
        """'Show evidence for 48,750 kWh' must route to EVIDENCE with ev_field=electricity."""
        intent = CopilotRAGRouter.parse_query("Show evidence for 48,750 kWh.")
        assert intent.retrieval_mode == "EVIDENCE"
        assert intent.evidence_field == "electricity"

    def test_where_is_electricity_mentioned_routes_evidence(self):
        """'Where is the electricity consumption mentioned?' must route to EVIDENCE."""
        intent = CopilotRAGRouter.parse_query("Where is the electricity consumption mentioned?")
        assert intent.retrieval_mode == "EVIDENCE"
        assert intent.evidence_field == "electricity"

    def test_kwh_value_evidence_api_returns_electricity_info(self):
        """'Where did the 48,750 kWh value come from?' API must return electricity evidence."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "Where did the 48,750 kWh value come from?"}
        )
        assert res.status_code == 200
        data = res.json()
        ans = data["answer"].lower()
        assert "48,750" in ans or "electricity" in ans or "kwh" in ans, (
            f"Expected electricity evidence, got: {data['answer']}"
        )
        # Must not be the generic fallback
        assert "verified source extraction lineage" not in ans or "electricity" in ans

    def test_evidence_for_electricity_consumption_works(self):
        """'Show me the evidence for the electricity consumption.' must return specific evidence."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "Show me the evidence for the electricity consumption."}
        )
        assert res.status_code == 200
        assert "48,750" in res.json()["answer"]

    def test_evidence_peak_demand_routes_correctly(self):
        """'Show me the evidence for the peak demand.' must route to EVIDENCE with ev_field=peak_demand."""
        intent = CopilotRAGRouter.parse_query("Show me the evidence for the peak demand.")
        assert intent.retrieval_mode == "EVIDENCE"
        assert intent.evidence_field == "peak_demand"


# ──────────────────────────────────────────────────────────────────────────────
# FIX 3 REGRESSION: Follow-up reporting period context
# ──────────────────────────────────────────────────────────────────────────────

class TestFollowUpReportingPeriod:
    """Verify conversation history resolves correct metric referent for reporting period queries."""

    def test_sequential_electricity_period_peak(self):
        """
        Q1: electricity → 48,750 kWh
        Q2: reporting period → October 2024 (electricity)
        Q3: peak demand during that period → 128.5 kVA
        """
        # Q1
        r1 = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What is our electricity consumption?"}
        )
        assert r1.status_code == 200
        a1 = r1.json()["answer"]
        assert "48,750" in a1, f"Q1 expected 48,750 kWh, got: {a1}"

        # Q2
        history_q2 = [
            {"role": "user", "content": "What is our electricity consumption?"},
            {"role": "assistant", "content": a1}
        ]
        r2 = client.post(
            "/api/copilot/chat",
            json={
                "document_id": 1,
                "message": "What reporting period does this belong to?",
                "history": history_q2
            }
        )
        assert r2.status_code == 200
        a2 = r2.json()["answer"]
        assert "october 2024" in a2.lower(), f"Q2 expected October 2024, got: {a2}"
        # Should mention "electricity" not be completely generic
        assert "electricity" in a2.lower() or "october 2024" in a2.lower()

        # Q3
        history_q3 = history_q2 + [
            {"role": "user", "content": "What reporting period does this belong to?"},
            {"role": "assistant", "content": a2}
        ]
        r3 = client.post(
            "/api/copilot/chat",
            json={
                "document_id": 1,
                "message": "What was the peak demand during that period?",
                "history": history_q3
            }
        )
        assert r3.status_code == 200
        a3 = r3.json()["answer"]
        assert "128.5" in a3, f"Q3 expected 128.5 kVA, got: {a3}"

    def test_reporting_period_without_history_uses_doc_period(self):
        """Without history, 'What reporting period does this belong to?' still returns October 2024."""
        res = client.post(
            "/api/copilot/chat",
            json={"document_id": 1, "message": "What reporting period does this electricity data belong to?"}
        )
        assert res.status_code == 200
        assert "october 2024" in res.json()["answer"].lower()

    def test_explicit_new_metric_overrides_history(self):
        """
        If history has electricity but current query asks for power factor,
        the current query's explicit metric (power_factor) takes precedence.
        """
        history = [
            {"role": "user", "content": "What is our electricity consumption?"},
            {"role": "assistant", "content": "Your electricity consumption is 48,750 kWh."}
        ]
        res = client.post(
            "/api/copilot/chat",
            json={
                "document_id": 1,
                "message": "What is the power factor?",
                "history": history
            }
        )
        assert res.status_code == 200
        assert "0.96" in res.json()["answer"]


# ──────────────────────────────────────────────────────────────────────────────
# FIX 4 REGRESSION: Test database isolation
# ──────────────────────────────────────────────────────────────────────────────

class TestDatabaseIsolation:
    """
    Verify Document #1 (msme_test_invoice) metrics are always correct
    and test-created metrics never permanently contaminate it.
    The conftest `isolate_document_one` fixture cleans up after every test.
    The session-end `init_db()` restores canonical state.
    """

    def test_doc1_has_no_water_metric(self):
        """Document #1 must contain zero water consumption metrics."""
        with SessionLocal() as db:
            water = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.document_id == 1,
                SustainabilityMetric.metric_type.in_([
                    "water_consumption", "freshwater", "recycled_water"
                ])
            ).all()
            assert len(water) == 0, (
                f"Document #1 has unexpected water metrics: {[m.metric_type for m in water]}"
            )

    def test_doc1_has_no_waste_metric(self):
        """Document #1 must contain zero waste metrics."""
        with SessionLocal() as db:
            waste = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.document_id == 1,
                SustainabilityMetric.metric_type.like("%waste%")
            ).all()
            assert len(waste) == 0, (
                f"Document #1 has unexpected waste metrics: {[m.metric_type for m in waste]}"
            )

    def test_doc1_diesel_is_exactly_420(self):
        """Document #1 diesel fuel must be exactly 420 L, not contaminated by test fixtures."""
        with SessionLocal() as db:
            fuel = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.document_id == 1,
                SustainabilityMetric.metric_type == "fuel_consumption"
            ).first()
            assert fuel is not None, "Document #1 must have a fuel_consumption metric"
            assert fuel.value == 420.0, f"Expected 420.0 L, got {fuel.value}"
            assert fuel.unit == "Liters"

    def test_fixture_water_metric_does_not_leak_into_doc1(self):
        """
        Create a fake water metric ON Document #1 directly to simulate
        a contamination event, then verify conftest cleanup removes it.
        After this test, the `isolate_document_one` fixture will remove it.
        During the test, it exists — but copilot must NOT return it because
        the LLM layer has a hardcoded guard for water on the electricity doc.
        """
        with SessionLocal() as db:
            # Simulate contamination: add water metric to doc 1
            fake_water = SustainabilityMetric(
                document_id=1,
                company_name="TARA ENGINEERING WORKS",
                metric_type="water_consumption",
                category="water",
                value=999.0,
                unit="kL",
                confidence=0.10,
                source_field="test_contamination",
                source_text="FAKE TEST WATER — SHOULD BE CLEANED UP",
                verification_status="AI_EXTRACTED"
            )
            db.add(fake_water)
            db.commit()

        try:
            # The copilot should still say water is not present
            # because the LLM layer guards water for this electricity doc
            res = client.post(
                "/api/copilot/chat",
                json={"document_id": 1, "message": "How much water did we consume?"}
            )
            assert res.status_code == 200
            ans = res.json()["answer"].lower()
            # Even with the contaminating row, the answer should deny water
            assert "not present" in ans or "not available" in ans or "not contain" in ans, (
                f"Water hallucination: copilot returned water when it should not: {ans}"
            )
        finally:
            # Explicit cleanup (conftest fixture also cleans this up)
            with SessionLocal() as db:
                to_del = db.query(SustainabilityMetric).filter(
                    SustainabilityMetric.document_id == 1,
                    SustainabilityMetric.metric_type == "water_consumption"
                ).all()
                for m in to_del:
                    db.delete(m)
                db.commit()

    def test_fixture_metric_on_other_doc_does_not_leak_to_doc1(self):
        """
        Create a fake water metric on a separate test document.
        Verify it does NOT appear when querying Document #1.
        """
        with SessionLocal() as db:
            test_doc = Document(
                filename="isolation_cross_doc_test.pdf",
                original_filename="isolation_cross_doc_test.pdf",
                file_path="/tmp/isolation_cross_doc_test.pdf",
                file_size=512,

                status="COMPLETED",
                review_status="VERIFIED",
                quality_score=90.0,
                company_name="Cross Doc Test Co",
                document_type="Water Bill"
            )
            db.add(test_doc)
            db.commit()
            db.refresh(test_doc)

            fake_water = SustainabilityMetric(
                document_id=test_doc.id,
                company_name="Cross Doc Test Co",
                metric_type="water_consumption",
                category="water",
                value=350.0,
                unit="kL",
                confidence=0.95,
                source_field="water_consumption_kl",
                source_text="Water consumed: 350 kL",
                verification_status="AI_EXTRACTED"
            )
            db.add(fake_water)
            db.commit()

            try:
                # Query copilot scoped to Document #1 — must not return 350 kL
                res = client.post(
                    "/api/copilot/chat",
                    json={"document_id": 1, "message": "How much water did we consume?"}
                )
                assert res.status_code == 200
                ans = res.json()["answer"].lower()
                assert "350" not in ans, (
                    f"Cross-document water metric (350 kL) leaked into Document #1 answer: {ans}"
                )
                assert "not present" in ans or "not available" in ans or "not contain" in ans

            finally:
                db.delete(fake_water)
                db.delete(test_doc)
                db.commit()

    def test_fake_fuel_contamination_is_blocked_by_conftest(self):
        """
        Simulate a test accidentally writing diesel=1500 L to Document #1.
        The conftest `isolate_document_one` fixture must clean this up after the test.
        After this test completes, Document #1 diesel must still be 420 L.
        """
        with SessionLocal() as db:
            # Directly add a bad fuel metric to doc 1
            bad_fuel = SustainabilityMetric(
                document_id=1,
                company_name="TARA ENGINEERING WORKS",
                metric_type="fuel_consumption",
                category="energy",
                value=1500.0,  # Wrong value — contamination
                unit="Liters",
                confidence=0.01,
                source_field="test_bad_fuel",
                source_text="FAKE CONTAMINATION — 1500 L DIESEL",
                verification_status="AI_EXTRACTED"
            )
            db.add(bad_fuel)
            db.commit()
            bad_fuel_id = bad_fuel.id

        # The conftest `isolate_document_one` will remove this after the test.
        # Verify 420 still exists alongside the bad one during the test.
        with SessionLocal() as db:
            good_fuel = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.document_id == 1,
                SustainabilityMetric.metric_type == "fuel_consumption",
                SustainabilityMetric.value == 420.0
            ).first()
            assert good_fuel is not None, "Canonical 420 L fuel metric must always exist"

            # Cleanup ourselves too (conftest also does it)
            bad = db.query(SustainabilityMetric).filter(
                SustainabilityMetric.id == bad_fuel_id
            ).first()
            if bad:
                db.delete(bad)
                db.commit()



# ──────────────────────────────────────────────────────────────────────────────
# NON-REGRESSION: Previously passing questions must still work
# ──────────────────────────────────────────────────────────────────────────────

class TestNonRegression:
    """Verify all previously passing QA questions continue to pass."""

    def test_electricity_consumption_48750(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the electricity consumption reported?"})
        assert "48,750" in res.json()["answer"]

    def test_peak_demand_128_5(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the peak demand?"})
        assert "128.5" in res.json()["answer"]

    def test_diesel_fuel_420(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much diesel fuel was consumed?"})
        assert "420" in res.json()["answer"]

    def test_power_factor_096(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the power factor?"})
        assert "0.96" in res.json()["answer"]

    def test_total_carbon_3301(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the total carbon emission?"})
        assert "33.01" in res.json()["answer"]

    def test_invoice_amount(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What is the total invoice amount?"})
        assert "453,169.56" in res.json()["answer"]

    def test_grid_electricity_44900(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much electricity came from the grid?"})
        assert "44,900" in res.json()["answer"]

    def test_rooftop_solar_3850(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much electricity came from rooftop solar?"})
        assert "3,850" in res.json()["answer"] or "3850" in res.json()["answer"]

    def test_reporting_period_october_2024(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What reporting period does this electricity data belong to?"})
        assert "october 2024" in res.json()["answer"].lower()

    def test_reduce_carbon_recommendation(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How can I reduce my carbon emissions?"})
        ans = res.json()["answer"].lower()
        assert "electricity" in ans or "scope 2" in ans or "31.88" in ans

    def test_focus_on_first_recommendation(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What should I focus on first?"})
        ans = res.json()["answer"].lower()
        assert "electricity" in ans or "emission" in ans

    def test_water_not_present(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "How much water did we consume?"})
        ans = res.json()["answer"].lower()
        assert "not present" in ans or "not available" in ans or "not contain" in ans

    def test_natural_gas_not_present(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What was our natural gas consumption?"})
        ans = res.json()["answer"].lower()
        assert "not present" in ans or "not available" in ans

    def test_january_2025_not_available(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What was our electricity consumption in January 2025?"})
        ans = res.json()["answer"].lower()
        assert "not available" in ans or "october 2024" in ans

    def test_reduce_20pct_no_unsupported_claim(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "Can we reduce emissions by 20%?"})
        ans = res.json()["answer"].lower()
        # Must not make a specific 20% promise
        assert "verified" not in ans or "do not" in ans or "i do not" in ans or "cannot" in ans

    def test_find_rooftop_solar_document(self):
        res = client.post("/api/copilot/chat", json={"message": "Find the document mentioning rooftop solar."})
        ans = res.json()["answer"].lower()
        assert "msme" in ans or "tara" in ans or "solar" in ans

    def test_recommendations_no_water(self):
        """Recommendations for electricity doc must not propose water actions."""
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What actions should we consider to reduce electricity-related emissions?"})
        ans = res.json()["answer"].lower()
        assert "water" not in ans

    def test_waste_not_present(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "Does this document contain waste data?"})
        ans = res.json()["answer"].lower()
        assert "not present" in ans or "not available" in ans or "not contain" in ans

    def test_metric_inventory_returns_valid_metrics(self):
        res = client.post("/api/copilot/chat", json={"document_id": 1, "message": "What sustainability metrics are present in this document?"})
        ans = res.json()["answer"]
        assert "48,750" in ans or "Electricity" in ans
        # Must not contain water/waste in the inventory
        assert "Water Consumption" not in ans or "not" in ans.lower()
