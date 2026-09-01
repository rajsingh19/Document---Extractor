import io
import logging
from typing import Tuple, Dict, Any
import pymupdf as fitz
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

class OCRService:
    @staticmethod
    def is_ocr_available() -> bool:
        """Check if Tesseract OCR binary is reachable."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def extract_text_ocr(cls, file_path: str, dpi: int = 300) -> Tuple[str, int, Dict[str, Any]]:
        """
        Extract text from scanned PDF pages using PyMuPDF pixmaps and pytesseract OCR fallback.
        Returns:
            Tuple of (extracted_ocr_text, page_count, metadata_dict)
        """
        doc = None
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            ocr_pages = []
            
            # Zoom matrix for high resolution OCR rendering
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            
            for page_index in range(page_count):
                page = doc[page_index]
                # Render PDF page to pixmap
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                
                # Convert pixmap to PIL Image
                image_bytes = pixmap.tobytes("png")
                pil_image = Image.open(io.BytesIO(image_bytes))
                
                # Image Pre-processing for improved OCR accuracy
                processed_image = pil_image.convert('L')  # Grayscale
                processed_image = processed_image.filter(ImageFilter.SHARPEN)
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.5)
                
                # Perform OCR
                page_text = pytesseract.image_to_string(processed_image, config="--psm 6")
                cleaned_text = "\n".join([line.strip() for line in page_text.splitlines() if line.strip()])
                
                if cleaned_text:
                    ocr_pages.append(f"--- PAGE {page_index + 1} (OCR) ---\n{cleaned_text}")
                    
            full_ocr_text = "\n\n".join(ocr_pages).strip()
            
            metadata = {
                "engine": "pytesseract",
                "dpi": dpi,
                "page_count": page_count,
                "total_characters": len(full_ocr_text),
                "is_empty": len(full_ocr_text.strip()) == 0
            }
            
            return full_ocr_text, page_count, metadata
            
        except Exception as e:
            logger.error(f"OCR fallback extraction failed for {file_path}: {e}")
            raise RuntimeError(f"OCR fallback extraction failed: {str(e)}")
        finally:
            if doc:
                doc.close()
