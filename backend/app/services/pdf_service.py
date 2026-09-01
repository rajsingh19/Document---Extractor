import pymupdf as fitz
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

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
