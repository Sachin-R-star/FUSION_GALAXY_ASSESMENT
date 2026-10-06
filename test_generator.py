"""
test_generator.py - Comprehensive Test Suite for Claim Report Generator

Tests parsing, reconciliation audit engine, edge cases (missing/null data),
and end-to-end report generation (HTML, XLSX, PDF).
"""

import os
import pytest
import shutil
from claim_parser import parse_claim_json, NOT_AVAILABLE
from audit_engine import run_claim_audit
from html_generator import generate_html_report
from excel_generator import generate_excel_report
from pdf_generator import generate_pdf_report
from generate_reports import process_single_claim

TEST_OUT_DIR = "test_output"

@pytest.fixture(scope="session", autouse=True)
def setup_teardown():
    os.makedirs(TEST_OUT_DIR, exist_ok=True)
    yield
    if os.path.exists(TEST_OUT_DIR):
        shutil.rmtree(TEST_OUT_DIR)

def test_parse_claim_a():
    claim_a_path = "CLAIM_A_data.json"
    if not os.path.exists(claim_a_path):
        pytest.skip(f"{claim_a_path} not found")

    claim = parse_claim_json(claim_a_path)
    assert claim.claim_ref == "CLAIM-A"
    assert claim.vehicle == "Hyundai Creta SX (SUV)"
    assert len(claim.parsed_estimate.lines) == 15
    assert claim.claims_system_amounts.estimated_amount_listed == 31650

def test_audit_engine_claim_a():
    claim_a_path = "CLAIM_A_data.json"
    if not os.path.exists(claim_a_path):
        pytest.skip(f"{claim_a_path} not found")

    claim = parse_claim_json(claim_a_path)
    audit = run_claim_audit(claim)

    assert audit.overall_status in ["CRITICAL DISCREPANCIES DETECTED", "MISMATCHES DETECTED"]
    assert len(audit.checks) > 0

    # Stated Total vs Sum of Parsed Lines mismatch check
    chk1 = next((c for c in audit.checks if c.check_id == "CHK_01"), None)
    assert chk1 is not None
    assert chk1.status == "MISMATCH"
    assert chk1.diff_amount == pytest.approx(18245.0, 0.1)

def test_missing_and_null_field_handling():
    """Verify that empty, null, or missing fields do not crash generator and fallback to 'not available'."""
    dummy_json = {
        "claim_ref": None,
        "vehicle": "",
        "loss_date": None,
        "parsed_estimate": {
            "stated_total_estimate_cost": None,
            "lines": [
                {
                    "part_name": None,
                    "part_type": None,
                    "part_quantity": None,
                    "part_total": None,
                    "part_dep_perc": None,
                    "part_gst_perc": None,
                    "total_final_amt": None
                }
            ]
        }
    }

    claim = parse_claim_json(dummy_json)
    assert claim.formatted_claim_ref == "UNKNOWN-CLAIM"
    assert claim.formatted_vehicle == NOT_AVAILABLE
    assert claim.formatted_loss_date == NOT_AVAILABLE

    audit = run_claim_audit(claim)
    assert audit is not None

    # HTML test
    html = generate_html_report(claim, audit)
    assert NOT_AVAILABLE in html

    # Excel test
    xlsx_path = os.path.join(TEST_OUT_DIR, "dummy_report.xlsx")
    generate_excel_report(claim, audit, xlsx_path)
    assert os.path.exists(xlsx_path)
    assert os.path.getsize(xlsx_path) > 0

    # PDF test
    pdf_path = os.path.join(TEST_OUT_DIR, "dummy_report.pdf")
    generate_pdf_report(claim, audit, pdf_path)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0

def test_end_to_end_all_claims():
    claims = ["CLAIM_A_data.json", "CLAIM_B_data.json", "CLAIM_C_data.json"]
    for c_path in claims:
        if os.path.exists(c_path):
            success = process_single_claim(c_path, TEST_OUT_DIR)
            assert success is True
