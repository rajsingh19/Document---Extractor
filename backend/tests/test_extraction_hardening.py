import pytest
from backend.app.utils.number_parser import parse_indian_number, normalize_number_for_matching
from backend.app.services.evidence_validator import EvidenceValidator
from backend.app.services.llm_service import LLMService
from backend.app.services.document_classifier import DocumentClassifier

def test_a_indian_currency_parsing():
    """Verify Indian currency amounts with various prefix and comma notations."""
    assert parse_indian_number("₹1,25,000") == 125000.0
    assert parse_indian_number("₹12,45,780.50") == 1245780.5
    assert parse_indian_number("Rs. 10,05,948.94") == 1005948.94
    assert parse_indian_number("INR 648,275.50") == 648275.5
    assert parse_indian_number("—") is None
    assert parse_indian_number("N/A") is None

def test_b_indian_quantity_parsing():
    """Verify Indian quantity numbers with units."""
    assert parse_indian_number("1,25,500.00 kWh") == 125500.0
    assert parse_indian_number("1,200.50 Liters") == 1200.5
    assert parse_indian_number("82,450 kWh") == 82450.0
    assert parse_indian_number("36,380.00 kL") == 36380.0

def test_c_currency_vs_consumption_disambiguation():
    """Ensure financial totals are not confused with energy consumption quantities."""
    text = """
    MAHALAXMI HEAVY ENGINEERING TAX INVOICE
    Item Description | Qty | Unit | Rate | Amount
    Grid Electricity Supply | 100,000.00 | kWh | 0.72 | 72,000.00
    Diesel Generator Backup Fuel | 1,000.00 | Liters | 10.00 | 10,000.00
    Net Invoice Total Payable Amount: INR 1,00,000.00
    """
    llm = LLMService()
    extracted = llm._heuristic_fallback_extraction(text)
    assert extracted["energy"]["electricity_kwh"] == 100000.0
    assert extracted["energy"]["fuel_diesel_liters"] == 1000.0
    assert extracted["energy"]["total_energy_cost_inr"] == 100000.0

def test_d_hsn_vs_quantity_disambiguation():
    """Ensure HSN identifiers like 27101930 are not parsed as fuel quantities."""
    text = """
    SHIVAM HIGHWAY PETROLEUM LOGISTICS
    Invoice No: INV-998877
    HSN Code: 27101930 (Mineral Diesel)
    Item: Diesel Generator Industrial Fuel
    Volume Dispatched: 1,200 Liters
    Total Invoice Amount: INR 127,500.00
    """
    llm = LLMService()
    extracted = llm._heuristic_fallback_extraction(text)
    assert extracted["energy"]["fuel_diesel_liters"] == 1200.0
    assert extracted["energy"]["fuel_diesel_liters"] != 27101930

def test_e_invoice_number_vs_sustainability_metrics():
    """Ensure invoice identifiers are never extracted as numerical sustainability metrics."""
    text = """
    Kaveri Auto Parts
    Invoice Ref: INV-998877
    Meter Serial: 100000
    Active Consumption: 45,200.00 kWh
    """
    llm = LLMService()
    extracted = llm._heuristic_fallback_extraction(text)
    assert extracted["energy"]["electricity_kwh"] == 45200.0
    assert extracted["energy"]["electricity_kwh"] != 998877
    assert extracted["energy"]["electricity_kwh"] != 100000

def test_f_table_row_integrity():
    """Verify table row line items maintain item description, quantity, and amount relationships."""
    text = """
    RAJASTHAN PRECISION METALS TAX INVOICE
    Item Description | Quantity | Unit | Unit Rate | Total Amount
    Steel Sheets Cold Rolled | 250.00 | kg | 145.00 | 36,250.00
    Aluminium Extrusion Rods | 120.00 | kg | 280.00 | 33,600.00
    Copper Wire Spools 2.5mm | 75.00 | kg | 620.00 | 46,500.00
    Net Invoice Total Payable Amount: INR 1,37,293.00
    """
    llm = LLMService()
    extracted = llm._heuristic_fallback_extraction(text)
    line_items = extracted.get("line_items", [])
    assert len(line_items) == 3
    assert line_items[0]["item_description"] == "Steel Sheets Cold Rolled"
    assert line_items[0]["quantity"] == 250.0
    assert line_items[0]["total_amount"] == 36250.0

def test_g_evidence_validation_success():
    """Verify that evidence with verbatim text in document validates successfully."""
    doc_text = "Total Active Electricity Consumption 82,450.00 kWh metered for October 2024."
    is_valid, conf, note = EvidenceValidator.validate_field_evidence(
        field_name="electricity_kwh",
        extracted_value=82450.0,
        unit="kWh",
        source_text="Total Active Electricity Consumption 82,450.00 kWh",
        document_text=doc_text
    )
    assert is_valid is True
    assert conf >= 0.90

def test_h_evidence_validation_unit_mismatch_failure():
    """Verify that evidence with contradictory units fails validation."""
    doc_text = "Fuel Delivery Receipt: High Speed Diesel 850.50 Liters delivered."
    is_valid, conf, note = EvidenceValidator.validate_field_evidence(
        field_name="electricity_kwh",
        extracted_value=850.5,
        unit="kWh",
        source_text="High Speed Diesel 850.50 Liters",
        document_text=doc_text
    )
    assert is_valid is False
    assert "Unit conflict" in note

def test_i_missing_evidence_penalty():
    """Verify that extracted fields without source text evidence receive lower quality scores."""
    llm = LLMService()
    payload = {
        "document_type": "Electricity Bill",
        "company": {"name": "Test MSME"},
        "period": {"billing_month": "October 2024"},
        "energy": {"electricity_kwh": 50000.0, "total_energy_cost_inr": 250000.0},
        "evidence": []  # Missing evidence
    }
    enriched = llm._enrich_quality_metrics(payload, extraction_method="pymupdf")
    assert enriched["metadata"]["review_status"] == "NEEDS_REVIEW"
    assert enriched["quality_summary"]["scoring_breakdown"]["evidence_penalty"] > 0

def test_j_cross_field_inconsistency_review_flag():
    """Verify that inconsistent field relationships flag the document for human review."""
    llm = LLMService()
    # Solar generation > Total electricity
    payload = {
        "document_type": "Electricity Bill",
        "company": {"name": "Test MSME"},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": 50000.0, 
            "renewable_energy_kwh": 75000.0,
            "total_energy_cost_inr": 250000.0
        },
        "evidence": [
            {"field": "electricity_kwh", "value": 50000.0, "source_text": "50000 kWh", "confidence_level": "HIGH"},
            {"field": "total_energy_cost_inr", "value": 250000.0, "source_text": "INR 250000", "confidence_level": "HIGH"}
        ]
    }
    enriched = llm._enrich_quality_metrics(payload, extraction_method="pymupdf")
    assert enriched["metadata"]["review_status"] == "NEEDS_REVIEW"
    assert any("Renewable captive generation exceeds" in r for r in enriched["quality_summary"]["review_reasons"])
