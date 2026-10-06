"""
generate_reports.py - Command Line Interface & Report Generator Engine

Generates PDF, Excel (.xlsx), and HTML claim audit reports for claim JSON files.

Usage:
  python generate_reports.py --all
  python generate_reports.py --json CLAIM_A_data.json
  python generate_reports.py --json CLAIM_B_data.json --out custom_output_dir
"""

import os
import sys
import glob
import argparse
from typing import List

# Ensure UTF-8 stdout encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from claim_parser import parse_claim_json, ClaimData
from audit_engine import run_claim_audit, AuditReport
from html_generator import generate_html_report
from excel_generator import generate_excel_report
from pdf_generator import generate_pdf_report

def process_single_claim(json_path: str, output_dir: str) -> bool:
    """Parses one claim JSON and produces HTML, Excel, and PDF reports."""
    print(f"\n[+] Processing Claim File: {os.path.basename(json_path)}")
    try:
        claim: ClaimData = parse_claim_json(json_path)
        audit: AuditReport = run_claim_audit(claim)

        os.makedirs(output_dir, exist_ok=True)
        base_name = f"{claim.claim_ref}_report"

        html_path = os.path.join(output_dir, f"{base_name}.html")
        excel_path = os.path.join(output_dir, f"{base_name}.xlsx")
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        # 1. HTML Generation
        html_content = generate_html_report(claim, audit)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  |-- HTML Report : {html_path}")

        # 2. Excel Generation
        generate_excel_report(claim, audit, excel_path)
        print(f"  |-- Excel Report: {excel_path}")

        # 3. PDF Generation
        generate_pdf_report(claim, audit, pdf_path)
        print(f"  +-- PDF Report  : {pdf_path}")

        # Print Audit Brief
        print(f"  ==> Audit Status: [{audit.overall_status}] ({audit.total_mismatches_count} Mismatches Detected)")
        for check in audit.checks:
            if check.status == "MISMATCH":
                print(f"      - {check.check_id}: {check.title} (Diff: INR {check.diff_amount:,.2f})")
        return True

    except Exception as e:
        print(f"  [!] ERROR processing {json_path}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Insurance Claim Report Generator (PDF, Excel, HTML)")
    parser.add_argument("--json", type=str, help="Path to a single claim JSON file")
    parser.add_argument("--all", action="store_true", help="Process all CLAIM_*_data.json files in workspace")
    parser.add_argument("--out", type=str, default="output", help="Target output directory (default: output)")

    args = parser.parse_args()

    # Default to --all if no specific arguments provided
    if not args.json and not args.all:
        args.all = True

    json_files: List[str] = []
    if args.json:
        if not os.path.exists(args.json):
            print(f"Error: Specified JSON file '{args.json}' does not exist.")
            sys.exit(1)
        json_files.append(args.json)
    elif args.all:
        pattern = "*_data.json"
        json_files = sorted(glob.glob(pattern))
        if not json_files:
            json_files = sorted(glob.glob(os.path.join(".", "*_data.json")))

    if not json_files:
        print("No claim JSON files found to process.")
        sys.exit(1)

    print("=========================================================================")
    print("      CLAIM REPORT GENERATOR - Fusion Galaxxy Assignment Submission     ")
    print("=========================================================================")
    print(f"Found {len(json_files)} claim file(s) to process. Output directory: '{args.out}'")

    success_count = 0
    for file_p in json_files:
        if process_single_claim(file_p, args.out):
            success_count += 1

    print("\n=========================================================================")
    print(f"BATCH COMPLETE: Successfully processed {success_count}/{len(json_files)} claim reports.")
    print(f"All reports (PDF, Excel, HTML) saved in '{os.path.abspath(args.out)}'")
    print("=========================================================================")

if __name__ == "__main__":
    main()
