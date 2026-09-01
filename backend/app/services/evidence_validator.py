import re
from typing import Dict, Any, List, Optional, Tuple
from backend.app.utils.number_parser import parse_indian_number, normalize_number_for_matching

class EvidenceValidator:
    """
    Deterministic validator that checks whether an extracted field's evidence:
    1. Verifiably exists in the document text.
    2. Contains the extracted value or its number-formatted equivalent.
    3. Has consistent unit semantics.
    """

    @staticmethod
    def validate_field_evidence(
        field_name: str,
        extracted_value: Any,
        unit: Optional[str],
        source_text: Optional[str],
        document_text: str
    ) -> Tuple[bool, float, str]:
        """
        Validates an evidence entry.
        Returns:
            Tuple of (is_valid: bool, adjusted_confidence: float, validation_notes: str)
        """
        if not source_text or not source_text.strip():
            return False, 0.40, "Evidence source_text is empty or missing."

        if not document_text or not document_text.strip():
            return False, 0.30, "Document text is empty."

        clean_source = " ".join(source_text.strip().split()).lower()
        clean_doc = " ".join(document_text.strip().split()).lower()

        # 1. Check if source_text exists in document text
        # Try direct containment
        occurs_in_doc = clean_source in clean_doc
        if not occurs_in_doc:
            # Check key tokens containment
            tokens = [t for t in clean_source.split() if len(t) > 2]
            matching_tokens = sum(1 for t in tokens if t in clean_doc)
            if tokens and (matching_tokens / len(tokens)) >= 0.8:
                occurs_in_doc = True

        if not occurs_in_doc:
            return False, 0.45, "Source text excerpt was not found in document text."

        # 2. Check if extracted value is represented in source_text
        if extracted_value is not None:
            if isinstance(extracted_value, (int, float)):
                candidates = normalize_number_for_matching(float(extracted_value))
                has_value = any(c.lower() in clean_source for c in candidates)
                if not has_value:
                    # Try finding numbers directly in source_text
                    all_nums = []
                    for raw_num in re.findall(r'[\d,]+(?:\.\d+)?', source_text):
                        pn = parse_indian_number(raw_num)
                        if pn is not None:
                            all_nums.append(pn)

                    if any(abs(n - float(extracted_value)) <= 0.5 for n in all_nums):
                        has_value = True
                    elif all_nums and abs(sum(all_nums) - float(extracted_value)) <= 0.5:
                        has_value = True
                    elif len(all_nums) >= 2:
                        # Check subset sums (e.g. 14.2 + 7.5 = 21.7 when 1 from Scope 1 is also present)
                        from itertools import combinations
                        for r in range(2, min(len(all_nums) + 1, 5)):
                            for combo in combinations(all_nums, r):
                                if abs(sum(combo) - float(extracted_value)) <= 0.5:
                                    has_value = True
                                    break
                            if has_value:
                                break

                if not has_value:
                    return False, 0.55, f"Source text '{source_text}' does not contain expected value {extracted_value}."

            elif isinstance(extracted_value, str) and len(extracted_value.strip()) > 2:
                val_clean = extracted_value.strip().lower()
                if val_clean not in clean_source:
                    # Check token overlap
                    val_tokens = val_clean.split()
                    token_match = sum(1 for t in val_tokens if t in clean_source)
                    if not val_tokens or (token_match / len(val_tokens)) < 0.6:
                        return False, 0.55, f"Source text does not match extracted string '{extracted_value}'."

        # 3. Unit validation
        if unit:
            unit_clean = unit.strip().lower()
            conflicting_units = {
                "kwh": ["liters", "litres", "kl", "kg"],
                "liters": ["kwh", "kl", "kg"],
                "kl": ["kwh", "liters", "kg"],
                "kg": ["kwh", "liters", "kl"],
                "inr": ["kwh", "liters", "kl", "kg", "tco2e"]
            }
            # Check if source text explicitly claims a conflicting unit
            if unit_clean in conflicting_units:
                for conflict in conflicting_units[unit_clean]:
                    if re.search(r'\b' + re.escape(conflict) + r'\b', clean_source):
                        # If unit specifies kWh but source text only has Liters, it's a conflict
                        if not re.search(r'\b' + re.escape(unit_clean) + r'\b', clean_source):
                            return False, 0.50, f"Unit conflict: expected '{unit}' but source text contains '{conflict}'."

        return True, 0.98, "Evidence verified against verbatim source text."

    @staticmethod
    def validate_all_evidence(evidence_list: List[Dict[str, Any]], document_text: str, extraction_method: str = "pymupdf") -> List[Dict[str, Any]]:
        """
        Validate and update an entire list of evidence records with verified confidence scores.
        """
        validated_list = []
        for item in evidence_list:
            if not isinstance(item, dict):
                continue
            field = item.get("field", "")
            val = item.get("value")
            unit = item.get("unit")
            source_text = item.get("source_text")

            is_valid, conf, note = EvidenceValidator.validate_field_evidence(
                field_name=field,
                extracted_value=val,
                unit=unit,
                source_text=source_text,
                document_text=document_text
            )

            if extraction_method == "ocr_fallback" and conf > 0.85:
                conf = 0.80

            updated = dict(item)
            updated["is_verified"] = item.get("is_verified", False)
            updated["confidence"] = conf
            updated["confidence_level"] = "HIGH" if conf >= 0.9 else ("MEDIUM" if conf >= 0.7 else "LOW")
            if note:
                updated["validation_note"] = note
            validated_list.append(updated)

        return validated_list
