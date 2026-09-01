import pymupdf as fitz
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class DocumentTextBlock(BaseModel):
    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Text content within the block")
    block_type: str = Field("text", description="text, table_row, or header")
    bounding_box: Optional[Tuple[float, float, float, float]] = Field(None, description="Bounding box (x0, y0, x1, y1)")

class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, int, Dict[str, Any]]:
        """
        Extract text from a PDF file using PyMuPDF (fitz).
        Returns:
            Tuple of (extracted_text, page_count, metadata_dict)
        """
        doc = None
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            extracted_pages = []
            
            for page_index in range(page_count):
                page = doc[page_index]
                text = page.get_text("text") or ""
                # Strip excessive blank lines while preserving table structure
                cleaned_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
                if cleaned_text:
                    extracted_pages.append(f"--- PAGE {page_index + 1} ---\n{cleaned_text}")
                    
            full_text = "\n\n".join(extracted_pages).strip()
            
            metadata = {
                "format": doc.metadata.get("format", "PDF"),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "page_count": page_count,
                "total_characters": len(full_text),
                "is_empty": len(full_text.strip()) == 0
            }
            
            return full_text, page_count, metadata
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {file_path}: {e}")
            raise RuntimeError(f"PyMuPDF text extraction failed: {str(e)}")
        finally:
            if doc:
                doc.close()

    @staticmethod
    def extract_structured_blocks(file_path: str) -> List[DocumentTextBlock]:
        """
        Extract structured layout blocks with page numbers, text, and bounding boxes.
        """
        doc = None
        blocks: List[DocumentTextBlock] = []
        try:
            doc = fitz.open(file_path)
            for page_idx, page in enumerate(doc):
                raw_blocks = page.get_text("blocks") or []
                for b in raw_blocks:
                    # b format: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(b) >= 5:
                        b_text = str(b[4]).strip()
                        if b_text:
                            b_type = "table_row" if "|" in b_text or "\t" in b_text else "text"
                            bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                            blocks.append(DocumentTextBlock(
                                page_number=page_idx + 1,
                                text=b_text,
                                block_type=b_type,
                                bounding_box=bbox
                            ))
            return blocks
        except Exception as e:
            logger.warning(f"Structured block extraction failed for {file_path}: {e}")
            return []
        finally:
            if doc:
                doc.close()
