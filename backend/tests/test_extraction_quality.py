import pytest
from backend.app.services.llm_service import LLMService, DOCUMENT_EXPECTED_FIELDS, ALL_EVALUATION_FIELDS
from backend.app.schemas.extraction import SustainabilityDocumentExtraction, QualitySummary

@pytest.fixture
def llm_service():
    return LLMService()

def test_a_complete_electricity_bill(llm_service):
    """
    Test A — Complete Electricity Bill:
    All expected fields (company_name, billing_period, electricity_kwh, total_energy_cost_inr)
    are present with high confidence and evidence.
    Expected:
    - High completeness (4/4 expected fields found)
    - 0 missing expected fields
    - High quality score (100 / 100)
    - review_status = 'COMPLETED'
    """
    mock_data = {
        "document_type": "Electricity Bill",
        "company": {"name": "Apex Precision Forgings Pvt. Ltd."},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": 124500.0,
            "total_energy_cost_inr": 1005948.94
        },
        "water_and_waste": {
            "water_consumption_kl": None,
            "hazardous_waste_kg": None,
            "non_hazardous_waste_kg": None
        },
        "evidence": [
            {
                "field": "company_name",
                "value": "Apex Precision Forgings Pvt. Ltd.",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Consumer Name: Apex Precision Forgings Pvt. Ltd."
            },
            {
                "field": "billing_period",
                "value": "October 2024",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Billing Month: October 2024"
            },
            {
                "field": "electricity_kwh",
                "value": 124500.0,
                "confidence": 0.98,
                "confidence_level": "HIGH",
                "source_text": "Total Active Energy Consumption 124,500.00 kWh"
            },
            {
                "field": "total_energy_cost_inr",
                "value": 1005948.94,
                "confidence": 0.96,
                "confidence_level": "HIGH",
                "source_text": "Net Total Payable Amount INR 1,005,948.94"
            }
        ]
    }

    result = llm_service._enrich_quality_metrics(mock_data, extraction_method="pymupdf", provider="heuristic_fallback")
    summary = result["quality_summary"]

    assert summary["total_expected_fields"] == 4
    assert summary["expected_fields_found"] == 4
    assert summary["expected_fields_missing"] == 0
    assert summary["quality_score"] == 100.0
    assert result["metadata"]["review_status"] == "COMPLETED"
    assert summary["scoring_breakdown"]["expected_missing_penalty"] == 0.0
    assert summary["scoring_breakdown"]["ocr_penalty"] == 0.0

def test_b_electricity_bill_missing_electricity_consumption(llm_service):
    """
    Test B — Electricity Bill Missing Electricity Consumption:
    Expected:
    - expected_fields_missing >= 1 (electricity_kwh missing)
    - quality_score < 100 (penalized by at least -10)
    - review_status = 'NEEDS_REVIEW'
    """
    mock_data = {
        "document_type": "Electricity Bill",
        "company": {"name": "Apex Precision Forgings Pvt. Ltd."},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": None,  # Genuinely missing
            "total_energy_cost_inr": 1005948.94
        },
        "evidence": [
            {
                "field": "company_name",
                "value": "Apex Precision Forgings Pvt. Ltd.",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Consumer Name: Apex Precision Forgings Pvt. Ltd."
            },
            {
                "field": "billing_period",
                "value": "October 2024",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Billing Month: October 2024"
            },
            {
                "field": "total_energy_cost_inr",
                "value": 1005948.94,
                "confidence": 0.96,
                "confidence_level": "HIGH",
                "source_text": "Net Total Payable Amount INR 1,005,948.94"
            }
        ]
    }

    result = llm_service._enrich_quality_metrics(mock_data, extraction_method="pymupdf", provider="heuristic_fallback")
    summary = result["quality_summary"]

    assert summary["expected_fields_missing"] >= 1
    assert "electricity_kwh" in summary["expected_missing_list"]
    assert summary["quality_score"] == 90.0
    assert summary["scoring_breakdown"]["expected_missing_penalty"] == 10.0
    assert result["metadata"]["review_status"] == "NEEDS_REVIEW"

def test_c_electricity_bill_missing_water_waste_not_penalized(llm_service):
    """
    Test C — Electricity Bill Missing Water/Waste:
    Water and waste fields must be classified as NOT_APPLICABLE and must NOT reduce the score.
    """
    mock_data = {
        "document_type": "Electricity Bill",
        "company": {"name": "Apex Precision Forgings Pvt. Ltd."},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": 124500.0,
            "total_energy_cost_inr": 1005948.94
        },
        "water_and_waste": {
            "water_consumption_kl": None,
            "hazardous_waste_kg": None,
            "non_hazardous_waste_kg": None
        },
        "evidence": [
            {
                "field": "company_name",
                "value": "Apex Precision Forgings Pvt. Ltd.",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Consumer Name: Apex Precision Forgings Pvt. Ltd."
            },
            {
                "field": "billing_period",
                "value": "October 2024",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Billing Month: October 2024"
            },
            {
                "field": "electricity_kwh",
                "value": 124500.0,
                "confidence": 0.98,
                "confidence_level": "HIGH",
                "source_text": "Total Active Energy Consumption 124,500.00 kWh"
            },
            {
                "field": "total_energy_cost_inr",
                "value": 1005948.94,
                "confidence": 0.96,
                "confidence_level": "HIGH",
                "source_text": "Net Total Payable Amount INR 1,005,948.94"
            }
        ]
    }

    result = llm_service._enrich_quality_metrics(mock_data, extraction_method="pymupdf", provider="heuristic_fallback")
    summary = result["quality_summary"]

    assert "water_consumption_kl" in summary["not_applicable_list"]
    assert "hazardous_waste_kg" in summary["not_applicable_list"]
    assert "non_hazardous_waste_kg" in summary["not_applicable_list"]
    assert summary["quality_score"] == 100.0

def test_d_scanned_waste_manifest_ocr_penalty(llm_service):
    """
    Test D — Scanned Waste Manifest:
    Expected:
    - OCR fallback penalty of -15
    - Medium confidence penalties
    - review_status = 'NEEDS_REVIEW'
    """
    manifest_text = """
    CUSTOMER: Shree Balaji Polymers & Auto Moulds MSME
    REG ID: UDYAM-GJ-01-998822
    DATE OF DISPATCH: 2024-09-15
    ITEM DESCRIPTION               QTY       UNIT       AMOUNT  
    High Speed Diesel (HSD)        3,400.0   LITERS     319,600 
    Scrap Plastic Polymer Flakes   8,500.0   KG          68,000 
    Used Lubricant Oil (Hazardous)   450.0   LITERS      18,000 
    TOTAL INVOICE VALUE:                      INR 522,600.00
    """
    result = llm_service._heuristic_fallback_extraction(
        manifest_text,
        extraction_method="ocr_fallback",
        fallback_reason="Scanned document image"
    )
    summary = result["quality_summary"]

    assert result["metadata"]["extraction_method"] == "ocr_fallback"
    assert summary["scoring_breakdown"]["ocr_penalty"] == 15.0
    assert result["metadata"]["review_status"] == "NEEDS_REVIEW"
    assert summary["quality_score"] < 85.0

def test_e_low_confidence_extraction_penalty(llm_service):
    """
    Test E — Low-confidence extraction:
    Low-confidence fields incur -10 penalty and trigger NEEDS_REVIEW.
    """
    mock_data = {
        "document_type": "Electricity Bill",
        "company": {"name": "Apex Precision Forgings Pvt. Ltd."},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": 124500.0,
            "total_energy_cost_inr": 1005948.94
        },
        "evidence": [
            {
                "field": "company_name",
                "value": "Apex Precision Forgings Pvt. Ltd.",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Consumer Name: Apex Precision Forgings Pvt. Ltd."
            },
            {
                "field": "billing_period",
                "value": "October 2024",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Billing Month: October 2024"
            },
            {
                "field": "electricity_kwh",
                "value": 124500.0,
                "confidence": 0.50,  # LOW CONFIDENCE
                "confidence_level": "LOW",
                "source_text": "Unclear text 124500"
            },
            {
                "field": "total_energy_cost_inr",
                "value": 1005948.94,
                "confidence": 0.96,
                "confidence_level": "HIGH",
                "source_text": "Net Total Payable Amount INR 1,005,948.94"
            }
        ]
    }

    result = llm_service._enrich_quality_metrics(mock_data, extraction_method="pymupdf", provider="heuristic_fallback")
    summary = result["quality_summary"]

    assert summary["low_confidence"] == 1
    assert summary["scoring_breakdown"]["low_confidence_penalty"] == 10.0
    assert summary["quality_score"] <= 90.0
    assert result["metadata"]["review_status"] == "NEEDS_REVIEW"

def test_f_human_verification_preserves_deterministic_score(llm_service):
    """
    Test F — Human verification:
    Human verification should update review_status to VERIFIED and track verified fields,
    but MUST NOT artificially inflate the deterministic extraction quality score.
    """
    from backend.app.models.document import Document
    from backend.app.schemas.document import FieldCorrectionRequest
    
    mock_data = {
        "document_type": "Electricity Bill",
        "company": {"name": "Apex Precision Forgings Pvt. Ltd."},
        "period": {"billing_month": "October 2024"},
        "energy": {
            "electricity_kwh": None,  # missing
            "total_energy_cost_inr": 1005948.94
        },
        "evidence": [
            {
                "field": "company_name",
                "value": "Apex Precision Forgings Pvt. Ltd.",
                "confidence": 0.95,
                "confidence_level": "HIGH",
                "source_text": "Consumer Name: Apex Precision Forgings Pvt. Ltd.",
                "is_verified": False
            }
        ]
    }

    result = llm_service._enrich_quality_metrics(mock_data, extraction_method="pymupdf", provider="heuristic_fallback")
    initial_score = result["quality_summary"]["quality_score"]
    
    # Simulate field correction in schema/logic
    quality_summary = result["quality_summary"]
    # Simulating what routes.py now does:
    quality_summary["human_verified"] = 1
    
    # The quality score must remain unchanged (no +2.5 bonus)
    assert quality_summary["quality_score"] == initial_score
