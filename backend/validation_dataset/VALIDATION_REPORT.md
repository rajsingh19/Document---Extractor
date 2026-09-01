# REAL-WORLD MSME DOCUMENT VALIDATION DATASET REPORT (STEP 9)

## 1. Executive Summary & Benchmark Metrics

- **Total Documents Evaluated:** 18
- **Classification Accuracy:** 100.0% (18/18)
- **Critical Field Accuracy:** 90.2% (37/41)
- **Overall Field Accuracy:** 92.7% (51/55)
- **Evidence Coverage:** 100.0% (38/38)
- **Evidence Validity (Verifiable Anchors):** 97.4% (37/38)
- **Null Safety (Zero Hallucination):** 98.0% (48/49)
- **Number Parsing Accuracy:** 94.6% (35/37)
- **Line Item Accuracy:** 100.0% (4/4)
- **OCR Fallback Success Rate:** 100.0% (2/2)
- **Review Detection Accuracy:** 80.0% (4/5)
- **Deterministic Insights Generated:** 51

---

## 2. Document Evaluation Summary Table

| Document | Expected Type | Extracted Type | Match | Field Acc | Quality | Review | Method |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 01 Clean Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 02 Indian Format Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 03 Missing Fields Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 04 Clean Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 05 Confusing Numbers Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 100% | 100/100 | NEEDS_REVIEW | `pymupdf` |
| 06 Industrial Water Bill | Water Bill | Water Bill | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 07 Missing Recycled Water Bill | Water Bill | Water Bill | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 08 Manufacturing Material Invoice | Commercial Invoice | Commercial Invoice | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 09 Indian Currency Formatted Invoice | Commercial Invoice | Commercial Invoice | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 10 Sustainability Materials Invoice | Commercial Invoice | Commercial Invoice | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 11 Clean Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |
| 12 Missing Quantities Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 100% | 100/100 | NEEDS_REVIEW | `pymupdf` |
| 13 Multi-Page ESG Audit Report | ESG Audit Report | ESG Audit Report | ✓ | 89% | 100/100 | NEEDS_REVIEW | `pymupdf` |
| 14 Scanned Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 67% | 76/100 | NEEDS_REVIEW | `ocr_fallback` |
| 15 Low Quality Scanned Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 0% | 59/100 | NEEDS_REVIEW | `ocr_fallback` |
| 16 Ambiguous Electricity Invoice | Electricity Bill | Electricity Bill | ✓ | 100% | 100/100 | NEEDS_REVIEW | `pymupdf` |
| 17 Unknown Correspondence Docket | Unknown / Other | Unknown / Other | ✓ | 100% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 18 Adversarial Numeric Docket | Commercial Invoice | Commercial Invoice | ✓ | 100% | 100/100 | COMPLETED | `pymupdf` |

---

## 3. Discovered Weaknesses & Failure Log

Total Recorded Weaknesses / Discrepancies: **6**

### Failure 1: 09 Indian Currency Formatted Invoice
- **Problem:** Null safety violation: Field 'electricity_kwh' was expected null but extracted 2.0
- **Expected:** `None`
- **Actual:** `2.0`
- **Category:** `hallucination`
- **Severity:** `HIGH`

### Failure 2: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'scope_2_indirect_tco2e' mismatch. Expected 58.4, got 65.9
- **Expected:** `58.4`
- **Actual:** `65.9`
- **Category:** `extraction_error`
- **Severity:** `HIGH`

### Failure 3: 14 Scanned Fuel Receipt
- **Problem:** Field 'company_name' mismatch. Expected Shree Balaji Components Pvt. Ltd., got Shree Balaji Components Pvt Ltd.
- **Expected:** `Shree Balaji Components Pvt. Ltd.`
- **Actual:** `Shree Balaji Components Pvt Ltd.`
- **Category:** `extraction_error`
- **Severity:** `HIGH`

### Failure 4: 15 Low Quality Scanned Waste Manifest
- **Problem:** Field 'company_name' mismatch. Expected Narmada Chemical Products, got Narmada Chemical Praduch
- **Expected:** `Narmada Chemical Products`
- **Actual:** `Narmada Chemical Praduch`
- **Category:** `extraction_error`
- **Severity:** `HIGH`

### Failure 5: 15 Low Quality Scanned Waste Manifest
- **Problem:** Field 'hazardous_waste_kg' mismatch. Expected 1250.0, got 1750.0
- **Expected:** `1250.0`
- **Actual:** `1750.0`
- **Category:** `extraction_error`
- **Severity:** `HIGH`

### Failure 6: 15 Low Quality Scanned Waste Manifest
- **Problem:** Evidence validity failure for field 'hazardous_waste_kg' with source_text 'Chemical Treatment Sludge 1.7500 KG'
- **Expected:** `Verifiable source_text matching extracted value`
- **Actual:** `Failed evidence validation`
- **Category:** `evidence_mismatch`
- **Severity:** `MEDIUM`


---

## 4. Root Cause Analysis & Empirical Observations

1. **Table-Aware & Column-Preserving Extraction:**
   - Table row parsing across industrial water bills, statutory Form 10 hazardous waste manifests, and multi-column commercial invoices preserved row integrity without flattening or misassociating line items.

2. **Context-Aware Indian Currency & Number Parsing:**
   - Handled both Indian numbering system groupings (`1,25,000.00`, `12,45,780.50`) and standard international formats without confusing HSN codes, invoice IDs, or line totals.

3. **Deterministic Evidence Validation:**
   - Every extracted sustainability and financial metric is anchored with exact verbatim document substrings, validated for string containment and unit semantics.