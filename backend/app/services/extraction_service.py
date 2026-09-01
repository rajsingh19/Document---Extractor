import os
import logging
from sqlalchemy.orm import Session
from backend.app.models.document import Document
from backend.app.services.pdf_service import PDFService
from backend.app.services.ocr_service import OCRService
from backend.app.services.llm_service import LLMService
from backend.app.services.document_classifier import DocumentClassifier
from backend.app.services.normalization_service import NormalizationService
from backend.app.schemas.extraction import SustainabilityDocumentExtraction

logger = logging.getLogger(__name__)

class ExtractionPipelineService:
    def __init__(self):
        self.pdf_service = PDFService()
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
        self.classifier = DocumentClassifier(llm_service=self.llm_service)
        self.normalization_service = NormalizationService()

    def process_document(self, db: Session, document_id: int, force_ocr: bool = False) -> Document:
        """
        Execute end-to-end extraction pipeline:
        1. Extract text from PDF using PyMuPDF.
        2. Fallback to OCR (Tesseract) if text is empty or sparse (<50 chars) or if force_ocr=True.
        3. Automatic document classification & routing.
        4. Send text to LLM / heuristic extractor with routed document type.
        5. Validate with Pydantic schema and check for classification conflicts.
        6. Persist metadata, structured data, and normalize into SustainabilityMetric records.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        if not os.path.exists(doc.file_path):
            doc.status = "FAILED"
            doc.error_message = f"File not found on disk at {doc.file_path}"
            db.commit()
            db.refresh(doc)
            return doc

        try:
            # Step 1: Text extraction via PyMuPDF
            doc.status = "EXTRACTING_TEXT"
            db.commit()
            
            extracted_text = ""
            extraction_method = "pymupdf"
            page_count = 1

            if not force_ocr:
                try:
                    extracted_text, page_count, pdf_meta = self.pdf_service.extract_text(doc.file_path)
                    doc.page_count = page_count
                except Exception as pdf_err:
                    logger.warning(f"PyMuPDF failed on doc {doc.id}, will try OCR fallback: {pdf_err}")
                    extracted_text = ""

            # Step 2: OCR Fallback if text is absent or insufficient (< 50 chars)
            is_scanned_or_empty = len(extracted_text.strip()) < 50
            if force_ocr or is_scanned_or_empty:
                logger.info(f"Doc {doc.id}: Text is sparse ({len(extracted_text)} chars). Triggering Tesseract OCR fallback...")
                if self.ocr_service.is_ocr_available():
                    try:
                        ocr_text, ocr_pages, ocr_meta = self.ocr_service.extract_text_ocr(doc.file_path)
                        if len(ocr_text.strip()) > 0:
                            extracted_text = ocr_text
                            extraction_method = "ocr_fallback"
                            doc.page_count = ocr_pages
                        else:
                            logger.warning(f"Doc {doc.id}: OCR returned empty text.")
                    except Exception as ocr_err:
                        logger.error(f"Doc {doc.id}: OCR extraction error: {ocr_err}")
                else:
                    logger.warning("Doc {doc.id}: Tesseract OCR binary not found. Proceeding with PyMuPDF text.")

            if not extracted_text.strip():
                # Provide a placeholder if document is completely blank
                extracted_text = f"[No extractable text or characters found in document {doc.original_filename}]"

            doc.extracted_text = extracted_text
            doc.extraction_method = extraction_method

            # Step 3: Automatic Document Classification & Routing
            classification_res = self.classifier.classify_document(extracted_text, extraction_method=extraction_method)
            doc.classification = classification_res.model_dump()
            doc.document_type = classification_res.document_type

            # Step 4: Send extracted text to LLM / routed extractor
            doc.status = "RUNNING_LLM"
            db.commit()

            raw_extracted_dict = self.llm_service.extract_sustainability_data(
                extracted_text,
                extraction_method=extraction_method
            )

            # Step 5: Validate structured JSON with Pydantic
            doc.status = "VALIDATING"
            db.commit()

            validated_data = SustainabilityDocumentExtraction.model_validate(raw_extracted_dict)
            structured_json = validated_data.model_dump()

            # Classification Conflict Detection: Check if classifier and extractor disagree
            has_conflict = False
            if (
                classification_res.document_type != "Unknown / Other"
                and validated_data.document_type != "Unknown / Other"
                and classification_res.document_type != validated_data.document_type
            ):
                has_conflict = True
                classification_res.conflict = True
                classification_res.extractor_document_type = validated_data.document_type
                doc.classification = classification_res.model_dump()
                logger.warning(
                    f"Doc {doc.id}: Classification conflict detected! Classifier={classification_res.document_type}, Extractor={validated_data.document_type}"
                )

            # Save structured data and denormalized summary fields
            doc.structured_data = structured_json
            doc.company_name = validated_data.company.name
            doc.document_type = classification_res.document_type if classification_res.document_type != "Unknown / Other" else validated_data.document_type
            doc.reporting_period = validated_data.period.billing_month or validated_data.period.issue_date
            doc.confidence_score = validated_data.confidence_score
            doc.quality_score = validated_data.quality_summary.quality_score
            doc.quality_summary = validated_data.quality_summary.model_dump()
            
            # Review status handling
            if has_conflict or classification_res.confidence_level == "LOW" or classification_res.document_type == "Unknown / Other":
                doc.review_status = "NEEDS_REVIEW"
            else:
                doc.review_status = validated_data.metadata.review_status or "COMPLETED"

            doc.total_energy_kwh = validated_data.energy.electricity_kwh
            doc.total_emissions_tco2e = (
                validated_data.carbon_emissions.total_ghg_emissions_tco2e or 
                ((validated_data.carbon_emissions.scope_1_direct_tco2e or 0) + (validated_data.carbon_emissions.scope_2_indirect_tco2e or 0))
            )
            doc.total_water_kl = validated_data.water_and_waste.water_consumption_kl
            doc.total_waste_kg = (
                (validated_data.water_and_waste.non_hazardous_waste_kg or 0) + 
                (validated_data.water_and_waste.hazardous_waste_kg or 0)
            ) or None
            doc.compliance_status = validated_data.compliance.compliance_status

            doc.status = "COMPLETED"
            doc.error_message = None

            # Detect possible business record duplicates (same company + type + period)
            if doc.company_name and doc.document_type and doc.reporting_period:
                existing_business_match = db.query(Document).filter(
                    Document.company_name == doc.company_name,
                    Document.document_type == doc.document_type,
                    Document.reporting_period == doc.reporting_period,
                    Document.id != doc.id,
                    Document.status == "COMPLETED"
                ).first()
                if existing_business_match:
                    if not doc.structured_data:
                        doc.structured_data = {}
                    doc.structured_data["possible_duplicate"] = True
                    doc.structured_data["duplicate_document_id"] = existing_business_match.id
                    doc.structured_data["duplicate_warning"] = (
                        f"Possible duplicate: Document #{existing_business_match.id} ({existing_business_match.original_filename}) "
                        f"already exists for {doc.company_name} ({doc.document_type}, {doc.reporting_period})."
                    )

            db.commit()
            db.refresh(doc)

            # Step 6: Automatically normalize structured extraction into format-independent records
            try:
                self.normalization_service.normalize_extraction(db, doc)
            except Exception as norm_err:
                logger.error(f"Failed to normalize metrics for doc {doc.id}: {norm_err}")

            logger.info(f"Successfully processed document ID {doc.id} ({doc.original_filename}).")
            return doc

        except Exception as err:
            logger.exception(f"Pipeline error for document ID {doc.id}: {err}")
            doc.status = "FAILED"
            doc.error_message = str(err)
            db.commit()
            db.refresh(doc)
            return doc
