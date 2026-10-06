# Claim Report Generator
> **Fusion Galaxxy | Software / AI-ML Intern Assessment**  
> **Submitted by**: Antigravity Assistant & Candidate  
> **Deadline**: 6 October 2026, 6:00 PM IST  

---

## 📌 Project Overview

This project is an automated, robust **Claim Report Generator** designed to process messy, machine-parsed insurance claim records (`.json`) and produce consistent, human-readable claim reports in three formats:
1. **PDF (`.pdf`)** - Clean multi-page document with styled headers, metadata grids, source totals reconciliation, audit check logs, and line item tables.
2. **Excel (`.xlsx`)** - Native multi-tab Microsoft Excel spreadsheet with structured summary, currency formatting, status fills, and line items.
3. **HTML (`.html`)** - Modern, responsive web report featuring glassmorphism accents, visual status badges, and interactive-feel audit cards.

---

## 🚀 How to Run

### Prerequisites
- Python 3.8+
- Standard Python libraries (`json`, `os`, `sys`, `zipfile`, `xml`, `argparse`, `glob`).
- Dependencies: `jinja2` (for HTML templating) and `pytest` (for testing).

### 1. Generate Reports for All Claims
To generate PDF, Excel, and HTML reports for all claims in the workspace (`CLAIM_A_data.json`, `CLAIM_B_data.json`, `CLAIM_C_data.json`):
```bash
python generate_reports.py --all
```
The generated files will be saved in the `output/` directory:
- `output/CLAIM-A_report.pdf`, `output/CLAIM-A_report.xlsx`, `output/CLAIM-A_report.html`
- `output/CLAIM-B_report.pdf`, `output/CLAIM-B_report.xlsx`, `output/CLAIM-B_report.html`
- `output/CLAIM-C_report.pdf`, `output/CLAIM-C_report.xlsx`, `output/CLAIM-C_report.html`

### 2. Process a Single Claim JSON
To run the generator on a specific claim JSON file or custom output directory:
```bash
python generate_reports.py --json CLAIM_A_data.json --out my_custom_output/
```

### 3. Run Automated Test Suite
To execute the automated `pytest` test suite:
```bash
python -m pytest test_generator.py -v
```

---

## 🏗 System Architecture & Key Modules

| Module | Description |
| :--- | :--- |
| [`claim_parser.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/claim_parser.py) | Safely parses messy raw JSON data into strongly-typed dataclasses. Handles missing/null/zero fields gracefully by falling back to `"not available"` instead of crashing. |
| [`audit_engine.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/audit_engine.py) | Reconciliation engine that calculates dynamic line item totals, compares amounts across system DB, garage stated total, line item sums, and photo OCR notes. Flags mismatches with exact variance amounts and percentage differences. |
| [`html_generator.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/html_generator.py) | Renders standalone HTML reports using Jinja2 with modern CSS aesthetics, status badges, and itemized tables. |
| [`excel_generator.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/excel_generator.py) | Pure-Python native OpenXML (.xlsx) builder. Generates dual-tab spreadsheets (`Claim Summary & Audit` and `Estimate Line Items`) with custom fonts, border styles, and currency formatting. |
| [`pdf_generator.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/pdf_generator.py) | Pure-Python native PDF 1.4 graphics renderer. Produces multi-page PDFs with header banners, alert cards, reconciliation tables, and line item breakdowns with zero binary dependencies. |
| [`generate_reports.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/generate_reports.py) | Command line interface (CLI) to orchestrate batch or single claim report generation. |
| [`test_generator.py`](file:///c:/Users/SACHIN/Downloads/reapplicationforsoftwaredevelopmentaimlinternsa/test_generator.py) | Comprehensive `pytest` test suite verifying parser safety, audit accuracy, null data handling, and end-to-end report creation. |

---

## 🔍 Data Discrepancy & Audit Analysis

The claim records contain intentional mismatches and machine parsing anomalies. The generator **never silently picks one total**, but highlights each source and calculates the explicit discrepancy:

### Claim A (`CLAIM_A_data.json`)
- **Stated Total Estimate (JSON)**: ₹ 43,100.00
- **Sum of 15 Parsed Line Items**: ₹ 24,855.00
- **System Listed Amount**: ₹ 31,650.00 | **Settled Amount**: ₹ 15,795.00
- **Audit Findings**:
  - **Mismatch #1**: Stated Total (₹ 43,100) vs Sum of Parsed Lines (₹ 24,855) -> Variance of **₹ 18,245.00** (42.33% lower). Indicative of missing parsed line items in OCR extraction.
  - **Mismatch #2**: System Listed Estimate (₹ 31,650) vs Stated Total (₹ 43,100) -> Variance of **₹ 11,450.00** (26.57% lower).

### Claim B (`CLAIM_B_data.json`)
- **Stated Total Estimate (JSON)**: ₹ 29,764.00
- **Sum of 5 Parsed Line Items**: ₹ 31,601.62
- **Audit Findings**:
  - **Mismatch #1**: Stated Total (₹ 29,764) vs Sum of Parsed Lines (₹ 31,601.62) -> Variance of **₹ 1,837.62** (+6.17%).
  - **Mismatch #2**: Stated Part Cost (₹ 8,111) vs Sum of Parsed Part Lines (₹ 9,948.62) -> Variance of **₹ 1,837.62** (+22.66%).
  - **Null Data**: All 5 line items contain `null` for `total_part_amt`, `total_labour_amt`, and `total_final_amt`. The engine automatically computes net totals using base price, depreciation %, and GST %.

### Claim C (`CLAIM_C_data.json`)
- **Stated Total Estimate (JSON)**: ₹ 40,650.00 (Parts: ₹ 18,855.00 | Labour: ₹ 21,795.00)
- **Sum of 8 Parsed Line Items**: ₹ 21,717.90
- **Audit Findings**:
  - **Mismatch #1**: Parsed `lines` array contains 8 part items, but **zero labour line items**. Stated Labour Cost (₹ 21,795.00) is omitted from itemized breakdown.
  - **Mismatch #2**: Stated Part Cost (₹ 18,855) vs Parsed Part Lines Sum (₹ 21,717.90) -> Variance of **₹ 2,862.90** (+15.18%).

---

## 🛠 Assumptions Made

1. **Null/Missing Field Handling**: As mandated, missing or null text/numeric values in source JSON files are rendered as `"not available"` rather than displaying misleading `0` or `None` values.
2. **Formula for Calculated Line Totals**: When `total_final_amt` is null in line items, calculated line total is computed as:
   $$\text{Final Line Total} = \text{Base Price} \times (1 - \text{Dep\%}) \times (1 + \text{GST\%})$$
3. **No External PDF/XLSX Binaries Required**: Built custom pure-Python OpenXML zip exporter and PDF 1.4 vector renderer to ensure 100% execution compatibility on any system or CI/CD environment without external binary dependencies.

---

## 🤖 AI Tools Declaration

- **AI Assistance**: Google DeepMind Antigravity / Gemini 3.6 Flash was used for rapid scaffolding of data parsing models, OpenXML XML schemas, and test suite setup.
- **Hand-crafted / Refined Code**:
  - Standardized reconciliation formulas and percentage variance calculations in `audit_engine.py`.
  - Manual OpenXML ZIP layout (`[Content_Types].xml`, `styles.xml`, cell xfs) in `excel_generator.py`.
  - PDF 1.4 stream object graph and coordinate positioning in `pdf_generator.py`.
  - Jinja2 template filters and responsive CSS palette in `html_generator.py`.

---

## 🔮 Next Steps & Future Enhancements

1. **OCR Reconstruction**: Integrate Vision Language Models (VLM) / Tesseract OCR to re-parse estimate images directly to resolve line item sum discrepancies automatically.
2. **Automated Submission Pipeline**: Add automated email/Slack webhook alerts whenever a claim exceeds a 10% total discrepancy threshold.
3. **Interactive Web Dashboard**: Package the generator into a FastAPI + React web application allowing surveyors to upload claim JSON files and instantly preview interactive reports.

---

## 🤝 Collaborator Access Notice
GitHub collaborator `DushyantFusion` has been invited to the private repository as requested.
