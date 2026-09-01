import os
import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.sustainability_metric import SustainabilityMetric
from backend.app.services.extraction_service import ExtractionPipelineService
from backend.app.services.normalization_service import NormalizationService
from backend.app.utils.helpers import parse_period_key
from backend.app.utils.sample_generator import (
    generate_sample_electricity_bill,
    generate_sample_esg_audit_report
)

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_trends.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db
    db.close()

def test_duplicate_file_hash_detection(test_db, tmp_path):
    pdf_path = str(tmp_path / "sample_bill.pdf")
    generate_sample_electricity_bill(pdf_path)

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # First upload
    doc1 = Document(
        filename="bill_1.pdf",
        original_filename="sample_bill.pdf",
        file_path=pdf_path,
        file_size=len(file_bytes),
        file_hash=file_hash,
        mime_type="application/pdf",
        status="COMPLETED"
    )
    test_db.add(doc1)
    test_db.commit()
    test_db.refresh(doc1)

    # Simulated second upload of exact same file
    existing = test_db.query(Document).filter(
        Document.file_hash == file_hash,
        Document.status == "COMPLETED"
    ).first()

    assert existing is not None
    assert existing.id == doc1.id
    assert existing.file_hash == file_hash

def test_possible_duplicate_business_record(test_db, tmp_path):
    pdf_path1 = str(tmp_path / "doc1.pdf")
    pdf_path2 = str(tmp_path / "doc2.pdf")
    generate_sample_electricity_bill(pdf_path1)
    generate_sample_electricity_bill(pdf_path2)

    pipeline = ExtractionPipelineService()

    doc1 = Document(
        filename="doc1.pdf",
        original_filename="doc1.pdf",
        file_path=pdf_path1,
        file_size=os.path.getsize(pdf_path1),
        status="PENDING"
    )
    test_db.add(doc1)
    test_db.commit()
    test_db.refresh(doc1)
    pipeline.process_document(test_db, doc1.id)

    # Process second doc with same company + doc_type + period
    doc2 = Document(
        filename="doc2.pdf",
        original_filename="doc2.pdf",
        file_path=pdf_path2,
        file_size=os.path.getsize(pdf_path2),
        status="PENDING"
    )
    test_db.add(doc2)
    test_db.commit()
    test_db.refresh(doc2)
    pipeline.process_document(test_db, doc2.id)

    test_db.refresh(doc2)
    assert doc2.structured_data is not None
    assert doc2.structured_data.get("possible_duplicate") is True
    assert "Possible duplicate" in doc2.structured_data.get("duplicate_warning", "")

def test_multiple_periods_chronological_trend(test_db):
    # Insert 3 monthly metrics for Tara Engineering Works
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=48750.0,
        unit="kWh",
        period_start="October 2024",
        period_end="October 2024",
        source_field="energy.electricity_kwh",
        verification_status="AI_EXTRACTED"
    )
    m2 = SustainabilityMetric(
        document_id=2,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=52300.0,
        unit="kWh",
        period_start="November 2024",
        period_end="November 2024",
        source_field="energy.electricity_kwh",
        verification_status="AI_EXTRACTED"
    )
    m3 = SustainabilityMetric(
        document_id=3,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=49800.0,
        unit="kWh",
        period_start="December 2024",
        period_end="December 2024",
        source_field="energy.electricity_kwh",
        verification_status="AI_EXTRACTED"
    )
    test_db.add_all([m3, m1, m2])  # Unordered insert
    test_db.commit()

    records = test_db.query(SustainabilityMetric).filter(
        SustainabilityMetric.metric_type == "electricity_consumption"
    ).all()

    sorted_records = sorted(records, key=lambda m: parse_period_key(m.period_start))
    periods = [parse_period_key(m.period_start) for m in sorted_records]
    values = [m.value for m in sorted_records]

    assert periods == ["2024-10", "2024-11", "2024-12"]
    assert values == [48750.0, 52300.0, 49800.0]

def test_missing_period_never_fabricated(test_db):
    # Insert Oct and Dec only
    m1 = SustainabilityMetric(
        document_id=1,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=48750.0,
        unit="kWh",
        period_start="October 2024",
        period_end="October 2024",
        source_field="energy.electricity_kwh"
    )
    m3 = SustainabilityMetric(
        document_id=3,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=49800.0,
        unit="kWh",
        period_start="December 2024",
        period_end="December 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m1, m3])
    test_db.commit()

    records = test_db.query(SustainabilityMetric).filter(
        SustainabilityMetric.metric_type == "electricity_consumption"
    ).all()

    sorted_records = sorted(records, key=lambda m: parse_period_key(m.period_start))
    periods = [parse_period_key(m.period_start) for m in sorted_records]

    # Exactly 2 data points, NO November generated
    assert len(periods) == 2
    assert periods == ["2024-10", "2024-12"]

def test_period_over_period_change(test_db):
    m_prev = SustainabilityMetric(
        document_id=1,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=52300.0,
        unit="kWh",
        period_start="November 2024",
        source_field="energy.electricity_kwh"
    )
    m_curr = SustainabilityMetric(
        document_id=2,
        company_name="Tara Engineering Works",
        metric_type="electricity_consumption",
        category="energy",
        value=49800.0,
        unit="kWh",
        period_start="December 2024",
        source_field="energy.electricity_kwh"
    )
    test_db.add_all([m_prev, m_curr])
    test_db.commit()

    records = test_db.query(SustainabilityMetric).filter(
        SustainabilityMetric.metric_type == "electricity_consumption"
    ).all()
    sorted_records = sorted(records, key=lambda m: parse_period_key(m.period_start))

    curr = sorted_records[-1]
    prev = sorted_records[-2]
    abs_change = round(curr.value - prev.value, 2)
    pct_change = round(((curr.value - prev.value) / prev.value) * 100, 2)

    assert abs_change == -2500.0
    assert pct_change == -4.78
