# STEP 9: FAILURE ANALYSIS & ROOT CAUSE INVESTIGATION

This document catalogs every failure identified from running the Step 8 validation benchmark (`run_validation.py`) on the 18-document realistic MSME dataset.

---

## Summary of Weaknesses Discovered

| Category | Total Count | Impact |
|---|:---:|---|
| **missing_field** | 20 | High (Table columns, total payable fields, and company labels missed) |
| **extraction_error** | 3 | High (Multi-page ESG Scope 1/2 GHG disaggregation confusion) |
| **classification_error** | 2 | Medium (Ambiguous correspondence and adversarial dockets) |
| **evidence_missing** | 19 | High (Evidence coverage was only 50% due to unanchored heuristic extractions) |

---

## Detailed Failure Log & Root Cause Analysis

### 1. Total Energy Cost / Total Payable Amount Mappings
- **Documents:** `01_clean_electricity`, `02_indian_format_electricity`, `03_missing_fields_electricity`, `04_clean_fuel`, `05_confusing_numbers_fuel`, `14_scanned_fuel`, `18_adversarial_numeric`
- **Fields:** `total_energy_cost_inr`
- **Error Category:** `missing_field` / `field_context_error`
- **Why it happened:** The heuristic extractor was specifically searching for the exact phrase "energy cost" or "electricity charges", but utility bills and fuel dockets use terms like "Total Amount Payable", "Net Payable Invoice Total", "NET TOTAL PAID (INR)", "Total Invoice Amount", or "Total Invoice Value".
- **Proposed Fix:** Add context-aware total amount extraction that searches for `Total Amount Payable`, `Net Payable`, `Total Payable`, `Total Value`, `Net Invoice Total` in utility and fuel documents, validating currency units (INR/₹/Rs) and extracting exact line evidence.

### 2. Table-Structured Water Consumption & Recycling
- **Documents:** `06_industrial_water_bill`, `07_missing_recycled_water_bill`, `13_multipage_esg_report`
- **Fields:** `water_consumption_kl`, `recycled_water_kl`
- **Error Category:** `missing_field` / `table_extraction_error`
- **Why it happened:** In industrial water bills, metrics are laid out in tables (e.g. `Freshwater Municipal Intake | 8,450.00 | kL` and `Treated / Recycled Industrial Water | 2,100.00 | kL` or `Freshwater Municipal Withdrawal | 42,800.00 | kL`). The single-line keyword search missed these multi-column rows.
- **Proposed Fix:** Implement table row parser that scans table lines containing `Freshwater`, `Municipal Intake`, `Water Consumption`, `Treated`, `Recycled Water`, `Effluent` with units `kL`, `cubic meters`, or `m³`.

### 3. Statutory Waste Manifest Table Columns & Schedule Categories
- **Documents:** `11_clean_waste_manifest`, `12_missing_quantities_waste`, `13_multipage_esg`, `15_low_quality_scanned_waste`
- **Fields:** `hazardous_waste_kg`, `non_hazardous_waste_kg`
- **Error Category:** `missing_field` / `table_extraction_error`
- **Why it happened:** Waste manifests use Form 10 schedule descriptions such as `Chemical Sludge / Hazardous Waste | 3,250.00 | kg`, `Polymer Process Waste | 460.00 | kg`, `Chemical Treatment Sludge | 1,250.0 | KG`, or `Hazardous Waste Generated | 4,200.00 | kg`. Regex heuristics looking only for standalone "waste: X" missed these statutory table entries.
- **Proposed Fix:** Add statutory waste schedule and table parsing to identify hazardous waste (sludge, chemical waste, solvent, spent oil) and non-hazardous/recyclable waste (polymer, scrap, packaging) in kg or MT, with proper unit conversion.

### 4. Multi-Page ESG GHG Scope 1, Scope 2, and Total Disaggregation
- **Document:** `13_multipage_esg_report`
- **Fields:** `scope_1_direct_tco2e`, `scope_2_indirect_tco2e`, `total_ghg_emissions_tco2e`
- **Expected:** Scope 1 = `7.50`, Scope 2 = `58.40`, Total = `65.90`
- **Actual:** Scope 1 = `65.9`, Scope 2 = `65.9`, Total = `131.8`
- **Error Category:** `extraction_error` / `field_context_error`
- **Why it happened:** The heuristic parser found the total GHG value `65.90` and populated both Scope 1 and Scope 2 with `65.9`, then recalculated total as `65.9 + 65.9 = 131.8`.
- **Proposed Fix:** Separate Scope 1 Direct (`Scope 1 Direct`, `Diesel DG Sets & Fleet`), Scope 2 Indirect (`Scope 2 Indirect`, `Purchased Electricity`), and Total Operational GHG explicitly. Add cross-field consistency validation.

### 5. Company Name Extraction across Diverse Layout Headers
- **Documents:** `08_material_invoice`, `11_clean_waste_manifest`, `14_scanned_fuel_receipt`, `15_low_quality_scanned_waste`
- **Fields:** `company_name`
- **Error Category:** `missing_field`
- **Why it happened:** Company headers used prefixes:
  - `Buyer / Consignee: Rajasthan Precision Metals`
  - `Sender / Generator: Narmada Chemical Products`
  - `CUSTOMER: Shree Balaji Components Pvt. Ltd.`
  - `GENERATOR: Narmada Chemical Products`
  The company regex only looked for `Company:`, `Consumer Name:`, `Billed To:`.
- **Proposed Fix:** Expand company identifier prefix rules to include `Buyer / Consignee:`, `Buyer:`, `Consignee:`, `Sender / Generator:`, `Generator:`, `Customer:`.

### 6. Edge Case Document Classification
- **Documents:** `17_unknown_correspondence`, `18_adversarial_numeric`
- **Error Category:** `classification_error`
- **Why it happened:**
  - Document 17 (Administrative letter regarding trade expo) was classified as `Commercial Invoice` because it had words like `Total`, `INR`, `PO-441299`.
  - Document 18 (Commercial Invoice with Electricity line items) was classified as `Electricity Bill` because of high keyword density for `kWh` and `HSN 27160000`.
- **Proposed Fix:**
  - For Document 17: Administrative correspondence without table line items or formal billing tax schedules should default to `Unknown / Other`.
  - For Document 18: Distinguish commercial supply invoices containing multiple distinct items from standard utility bills.

### 7. Evidence Coverage & Traceability Hardening
- **Error Category:** `evidence_missing`
- **Why it happened:** Heuristic extractors extracted values without systematically building and anchoring `FieldEvidence` records with exact verbatim document substrings, lowering evidence coverage to 50%.
- **Proposed Fix:** Build a deterministic evidence extraction and validation layer. Every extracted field must capture its exact line substring from the document. Implement `EvidenceValidator` to verify string containment, numeric equivalence, and unit integrity.
