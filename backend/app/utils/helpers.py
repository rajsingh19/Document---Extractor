import os
import uuid
import re

def sanitize_filename(filename: str) -> str:
    """Clean and sanitize filename to prevent path traversal."""
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return clean

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename preserving the original extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext:
        ext = ".pdf"
    unique_id = uuid.uuid4().hex[:12]
    clean_name = sanitize_filename(os.path.splitext(original_filename)[0])
    return f"{clean_name}_{unique_id}{ext}"

def format_file_size(size_in_bytes: int) -> str:
    """Format bytes to KB / MB."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
