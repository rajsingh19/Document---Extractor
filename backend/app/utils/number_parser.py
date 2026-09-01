import re
from typing import Optional, Tuple, Any, List

def parse_indian_number(val_str: Any) -> Optional[float]:
    """
    Parse numbers formatted with Western or Indian comma groupings,
    currency symbols (₹, Rs, INR), and whitespace.
    Examples:
        '1,25,000' -> 125000.0
        '12,45,780.50' -> 1245780.5
        '1,25,500.00 kWh' -> 125500.0
        '1,200.50 Liters' -> 1200.5
        '₹ 10,05,948.94' -> 1005948.94
        'Rs. 77,608.13' -> 77608.13
    """
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return float(val_str)

    s = str(val_str).strip()
    if not s or s in ["—", "-", "N/A", "null", "None"]:
        return None

    # Remove currency prefixes, trailing units, and unwanted characters
    # Keep only digits, periods, commas, and minus sign
    clean = re.sub(r'^[^\d.-]+', '', s)
    clean = re.sub(r'[^\d.]+$', '', clean)

    # Remove commas
    clean = clean.replace(',', '').strip()

    # Extract first valid decimal number
    match = re.search(r'[-+]?\d+(?:\.\d+)?', clean)
    if not match:
        return None

    try:
        return float(match.group(0))
    except (ValueError, TypeError):
        return None

def normalize_number_for_matching(val: float) -> list:
    """
    Generate different string representations of a number (standard, Indian comma, no decimal)
    to match against source text.
    """
    if val is None:
        return []
    
    val_int = int(val) if val == int(val) else None
    results = [str(val)]
    if val_int is not None:
        results.append(str(val_int))
        results.append(f"{val_int:,}")  # standard Western comma: 125,000
        
        # Indian comma format
        s_int = str(val_int)
        if len(s_int) > 3:
            last3 = s_int[-3:]
            rest = s_int[:-3]
            # split rest into chunks of 2 from right to left
            parts = []
            while len(rest) > 2:
                parts.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                parts.insert(0, rest)
            indian_fmt = ",".join(parts) + "," + last3
            results.append(indian_fmt)

    # With 2 decimals
    results.append(f"{val:.2f}")
    if val_int is not None:
        results.append(f"{val_int:,}.00")

    return list(set(results))
