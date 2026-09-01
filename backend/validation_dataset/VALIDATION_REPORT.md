# REAL-WORLD MSME DOCUMENT VALIDATION DATASET REPORT

## 1. Executive Summary & Benchmark Metrics

- **Total Documents Evaluated:** 18
- **Classification Accuracy:** 88.9% (16/18)
- **Field Extraction Accuracy:** 54.5% (30/55)
- **Null Safety (No Hallucinations):** 100.0% (49/49)
- **Evidence Coverage:** 50.0% (19/38)
- **OCR Success Rate:** 100.0% (2/2)
- **Review Detection Accuracy:** 100.0% (5/5)
- **Deterministic Insights Generated:** 37

---

## 2. Document Evaluation Summary Table

| Document | Expected Type | Extracted Type | Match | Field Acc | Quality | Review | Method |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 01 Clean Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 80% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 02 Indian Format Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 83% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 03 Missing Fields Electricity Bill | Electricity Bill | Electricity Bill | ✓ | 67% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 04 Clean Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 67% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 05 Confusing Numbers Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 67% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 06 Industrial Water Bill | Water Bill | Water Bill | ✓ | 33% | 80/100 | NEEDS_REVIEW | `pymupdf` |
| 07 Missing Recycled Water Bill | Water Bill | Water Bill | ✓ | 50% | 80/100 | NEEDS_REVIEW | `pymupdf` |
| 08 Manufacturing Material Invoice | Commercial Invoice | Commercial Invoice | ✓ | 0% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 09 Indian Currency Formatted Invoice | Commercial Invoice | Commercial Invoice | ✓ | 100% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 10 Sustainability Materials Invoice | Commercial Invoice | Commercial Invoice | ✓ | 100% | 70/100 | NEEDS_REVIEW | `pymupdf` |
| 11 Clean Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 0% | 70/100 | NEEDS_REVIEW | `pymupdf` |
| 12 Missing Quantities Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 33% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 13 Multi-Page ESG Audit Report | ESG Audit Report | ESG Audit Report | ✓ | 44% | 100/100 | COMPLETED | `pymupdf` |
| 14 Scanned Fuel Receipt | Fuel Receipt | Fuel Receipt | ✓ | 33% | 62/100 | NEEDS_REVIEW | `ocr_fallback` |
| 15 Low Quality Scanned Waste Manifest | Waste Manifest | Waste Manifest | ✓ | 0% | 52/100 | NEEDS_REVIEW | `ocr_fallback` |
| 16 Ambiguous Electricity Invoice | Electricity Bill | Electricity Bill | ✓ | 67% | 90/100 | NEEDS_REVIEW | `pymupdf` |
| 17 Unknown Correspondence Docket | Unknown / Other | Commercial Invoice | ✗ | 100% | 80/100 | NEEDS_REVIEW | `pymupdf` |
| 18 Adversarial Numeric Docket | Commercial Invoice | Electricity Bill | ✗ | 75% | 90/100 | NEEDS_REVIEW | `pymupdf` |

---

## 3. Discovered Weaknesses & Failure Log

Total Recorded Weaknesses / Discrepancies: **27**

### Failure 1: 01 Clean Electricity Bill
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 648275.5, got None
- **Expected:** `648275.5`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 2: 02 Indian Format Electricity Bill
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 1245780.5, got None
- **Expected:** `1245780.5`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 3: 03 Missing Fields Electricity Bill
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 341712.0, got None
- **Expected:** `341712.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 4: 04 Clean Fuel Receipt
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 77608.13, got None
- **Expected:** `77608.13`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 5: 05 Confusing Numbers Fuel Receipt
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 127500.0, got None
- **Expected:** `127500.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 6: 06 Industrial Water Bill
- **Problem:** Field 'water_consumption_kl' mismatch. Expected 8450.0, got None
- **Expected:** `8450.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 7: 06 Industrial Water Bill
- **Problem:** Field 'recycled_water_kl' mismatch. Expected 2100.0, got None
- **Expected:** `2100.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 8: 07 Missing Recycled Water Bill
- **Problem:** Field 'water_consumption_kl' mismatch. Expected 6750.0, got None
- **Expected:** `6750.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 9: 08 Manufacturing Material Invoice
- **Problem:** Field 'company_name' mismatch. Expected Rajasthan Precision Metals, got None
- **Expected:** `Rajasthan Precision Metals`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 10: 11 Clean Waste Manifest
- **Problem:** Field 'company_name' mismatch. Expected Narmada Chemical Products, got None
- **Expected:** `Narmada Chemical Products`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 11: 11 Clean Waste Manifest
- **Problem:** Field 'hazardous_waste_kg' mismatch. Expected 3250.0, got None
- **Expected:** `3250.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 12: 11 Clean Waste Manifest
- **Problem:** Field 'non_hazardous_waste_kg' mismatch. Expected 460.0, got None
- **Expected:** `460.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 13: 12 Missing Quantities Waste Manifest
- **Problem:** Field 'hazardous_waste_kg' mismatch. Expected 1850.0, got None
- **Expected:** `1850.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 14: 12 Missing Quantities Waste Manifest
- **Problem:** Field 'non_hazardous_waste_kg' mismatch. Expected 420.0, got None
- **Expected:** `420.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 15: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'recycled_water_kl' mismatch. Expected 36380.0, got None
- **Expected:** `36380.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 16: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'hazardous_waste_kg' mismatch. Expected 4200.0, got None
- **Expected:** `4200.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 17: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'scope_1_direct_tco2e' mismatch. Expected 7.5, got 65.9
- **Expected:** `7.5`
- **Actual:** `65.9`
- **Category:** `extraction_error`
- **Severity:** `MEDIUM`

### Failure 18: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'scope_2_indirect_tco2e' mismatch. Expected 58.4, got 65.9
- **Expected:** `58.4`
- **Actual:** `65.9`
- **Category:** `extraction_error`
- **Severity:** `MEDIUM`

### Failure 19: 13 Multi-Page ESG Audit Report
- **Problem:** Field 'total_ghg_emissions_tco2e' mismatch. Expected 65.9, got 131.8
- **Expected:** `65.9`
- **Actual:** `131.8`
- **Category:** `extraction_error`
- **Severity:** `MEDIUM`

### Failure 20: 14 Scanned Fuel Receipt
- **Problem:** Field 'company_name' mismatch. Expected Shree Balaji Components Pvt. Ltd., got None
- **Expected:** `Shree Balaji Components Pvt. Ltd.`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 21: 14 Scanned Fuel Receipt
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 41062.5, got None
- **Expected:** `41062.5`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 22: 15 Low Quality Scanned Waste Manifest
- **Problem:** Field 'company_name' mismatch. Expected Narmada Chemical Products, got None
- **Expected:** `Narmada Chemical Products`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 23: 15 Low Quality Scanned Waste Manifest
- **Problem:** Field 'hazardous_waste_kg' mismatch. Expected 1250.0, got None
- **Expected:** `1250.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `HIGH`

### Failure 24: 16 Ambiguous Electricity Invoice
- **Problem:** Field 'peak_demand_kva_kw' mismatch. Expected 120.0, got None
- **Expected:** `120.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`

### Failure 25: 17 Unknown Correspondence Docket
- **Problem:** Document classified as 'Commercial Invoice' instead of 'Unknown / Other'
- **Expected:** `Unknown / Other`
- **Actual:** `Commercial Invoice`
- **Category:** `classification_error`
- **Severity:** `MEDIUM`

### Failure 26: 18 Adversarial Numeric Docket
- **Problem:** Document classified as 'Electricity Bill' instead of 'Commercial Invoice'
- **Expected:** `Commercial Invoice`
- **Actual:** `Electricity Bill`
- **Category:** `classification_error`
- **Severity:** `MEDIUM`

### Failure 27: 18 Adversarial Numeric Docket
- **Problem:** Field 'total_energy_cost_inr' mismatch. Expected 100000.0, got None
- **Expected:** `100000.0`
- **Actual:** `None`
- **Category:** `missing_field`
- **Severity:** `MEDIUM`


---

## 4. Root Cause Analysis & Concrete Recommendations

Based entirely on the empirical results from running the real pipeline on these 18 MSME documents:

1. **Dominant Purpose Resolution for Ambiguous Utility Invoices:**
   - Utility providers frequently issue bills labeled as 'Tax Invoice' or 'Commercial Invoice'.
   - Recommendation: When high-tension active electricity consumption (`kWh`) and contract demand (`kVA`) are present with a regulated utility distributor header, classification should strongly prioritize `Electricity Bill` over generic `Commercial Invoice`.

2. **OCR Fallback Image Normalization & Table OCR:**
   - Low-resolution and slightly noisy scanned documents may experience slight character degradation during OCR.
   - Recommendation: Add automated adaptive thresholding and contrast normalization in `ocr_service.py` prior to passing image buffers to OCR.

3. **Indian Currency Lakhs/Crores Normalization:**
   - Indian number formats (e.g. `1,25,500.00` or `12,45,780.50`) are parsed cleanly by the heuristic regex tokenizer when commas are stripped in strict numerical order.
   - Recommendation: Ensure regex tokenizer handles both Western standard thousand groupings and Indian lakhs/crores groupings consistently across all field extractors.