import os
import uuid
import re
from datetime import datetime

MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

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

def parse_period_key(period_str: str) -> str:
    """
    Standardize a reporting period string (e.g. 'October 2024', '2024-10', '2023-04-01')
    into a chronological sort key 'YYYY-MM'.
    """
    if not period_str:
        return "9999-99"

    s = str(period_str).strip()

    # Pattern 1: YYYY-MM or YYYY-MM-DD
    iso_match = re.search(r'(\d{4})[-/](\d{1,2})', s)
    if iso_match:
        year = iso_match.group(1)
        month = int(iso_match.group(2))
        return f"{year}-{month:02d}"

    # Pattern 2: Month YYYY (e.g. 'October 2024', 'Oct 2024')
    month_year_match = re.search(r'([a-zA-Z]+)[ \t]+(\d{4})', s)
    if month_year_match:
        month_name = month_year_match.group(1).lower()
        year = month_year_match.group(2)
        if month_name in MONTH_MAP:
            return f"{year}-{MONTH_MAP[month_name]}"

    # Pattern 3: YYYY (year only)
    year_match = re.search(r'\b(20\d{2})\b', s)
    if year_match:
        return f"{year_match.group(1)}-01"

    return s
