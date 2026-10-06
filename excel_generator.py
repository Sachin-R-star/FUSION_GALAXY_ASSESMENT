"""
excel_generator.py - Native OpenXML Excel (.xlsx) Report Generator

Generates a fully valid, beautifully formatted Microsoft Excel (.xlsx) spreadsheet
without requiring external third-party dependencies (uses standard library zipfile & xml).
Creates two structured worksheets:
1. 'Claim Summary & Audit' - Metadata, Totals Reconciliation, and Discrepancy Log.
2. 'Estimate Line Items' - Itemized breakdown table with unit costs, dep %, GST %, and totals.
"""

import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from typing import List, Dict, Any, Tuple, Optional
import os
from claim_parser import ClaimData, format_currency, format_percent, NOT_AVAILABLE
from audit_engine import AuditReport

class OpenXLSXWriter:
    """Lightweight, pure-Python OpenXML (.xlsx) generator."""

    def __init__(self):
        self.shared_strings: List[str] = []
        self.string_table: Dict[str, int] = {}
        self.sheets: List[Tuple[str, List[List[Any]]]] = []

    def _get_string_index(self, text: str) -> int:
        s = str(text)
        if s in self.string_table:
            return self.string_table[s]
        idx = len(self.shared_strings)
        self.string_table[s] = idx
        self.shared_strings.append(s)
        return idx

    def add_sheet(self, sheet_name: str, rows: List[List[Any]]):
        """Adds a sheet with rows of data (strings, numbers, or dicts with style)."""
        self.sheets.append((sheet_name, rows))

    def save(self, file_path: str):
        """Builds and writes the .xlsx zip archive."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as z:
            # 1. [Content_Types].xml
            z.writestr("[Content_Types].xml", self._build_content_types())
            
            # 2. _rels/.rels
            z.writestr("_rels/.rels", self._build_root_rels())

            # 3. xl/workbook.xml
            z.writestr("xl/workbook.xml", self._build_workbook())

            # 4. xl/_rels/workbook.xml.rels
            z.writestr("xl/_rels/workbook.xml.rels", self._build_workbook_rels())

            # 5. xl/styles.xml
            z.writestr("xl/styles.xml", self._build_styles())

            # 6. xl/sharedStrings.xml
            z.writestr("xl/sharedStrings.xml", self._build_shared_strings())

            # 7. xl/worksheets/sheetN.xml
            for idx, (name, rows) in enumerate(self.sheets, 1):
                z.writestr(f"xl/worksheets/sheet{idx}.xml", self._build_sheet(rows))

    def _build_content_types(self) -> str:
        sheets_xml = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(self.sheets) + 1)
        )
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
    <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
    {sheets_xml}
</Types>"""

    def _build_root_rels(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    def _build_workbook(self) -> str:
        sheets_xml = "".join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
            for i, (name, _) in enumerate(self.sheets, 1)
        )
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        {sheets_xml}
    </sheets>
</workbook>"""

    def _build_workbook_rels(self) -> str:
        sheets_rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(self.sheets) + 1)
        )
        styles_rid = f"rId{len(self.sheets) + 1}"
        ss_rid = f"rId{len(self.sheets) + 2}"
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {sheets_rels}
    <Relationship Id="{styles_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    <Relationship Id="{ss_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>"""

    def _build_styles(self) -> str:
        # Styles index mapping:
        # 0: Default
        # 1: Header bold fill navy (1E293B, white text)
        # 2: Section Title bold (1E1B4B, font 14)
        # 3: Subtitle / Label bold
        # 4: Currency format (₹ #,##0.00)
        # 5: Mismatch Rose Fill (FEE2E2, text 991B1B)
        # 6: Match Emerald Fill (D1FAE5, text 065F46)
        # 7: Bordered table cell
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <fonts count="4">
        <font><sz val="11"/><name val="Calibri"/></font>
        <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
        <font><b/><sz val="14"/><color rgb="FF1E1B4B"/><name val="Calibri"/></font>
        <font><b/><sz val="11"/><color rgb="FF0F172A"/><name val="Calibri"/></font>
    </fonts>
    <fills count="5">
        <fill><patternFill patternType="none"/></fill>
        <fill><patternFill patternType="gray125"/></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFD1FAE5"/><bgColor indexed="64"/></patternFill></fill>
    </fills>
    <borders count="2">
        <border><left/><right/><top/><bottom/></border>
        <border>
            <left style="thin"><color rgb="FFCBD5E1"/></left>
            <right style="thin"><color rgb="FFCBD5E1"/></right>
            <top style="thin"><color rgb="FFCBD5E1"/></top>
            <bottom style="thin"><color rgb="FFCBD5E1"/></bottom>
        </border>
    </borders>
    <cellStyleXfs count="1">
        <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
    </cellStyleXfs>
    <cellXfs count="8">
        <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
        <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
        <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
        <xf numFmtId="0" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/>
        <xf numFmtId="4" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
        <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
        <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
        <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    </cellXfs>
</styleSheet>"""

    def _build_shared_strings(self) -> str:
        items = "".join(f"<si><t>{escape(s)}</t></si>" for s in self.shared_strings)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(self.shared_strings)}" uniqueCount="{len(self.shared_strings)}">
    {items}
</sst>"""

    def _build_sheet(self, rows: List[List[Any]]) -> str:
        row_xml_list = []
        for r_idx, row in enumerate(rows, 1):
            cell_xml_list = []
            for c_idx, cell in enumerate(row, 1):
                col_letter = self._col_to_letter(c_idx)
                cell_ref = f"{col_letter}{r_idx}"
                
                # Check cell styling dict wrapper
                val = cell
                style_idx = 0
                if isinstance(cell, dict):
                    val = cell.get("val")
                    style_idx = cell.get("style", 0)

                if val is None:
                    continue

                if isinstance(val, (int, float)):
                    cell_xml = f'<c r="{cell_ref}" s="{style_idx}"><v>{val}</v></c>'
                else:
                    str_idx = self._get_string_index(str(val))
                    cell_xml = f'<c r="{cell_ref}" t="s" s="{style_idx}"><v>{str_idx}</v></c>'
                cell_xml_list.append(cell_xml)
            
            if cell_xml_list:
                row_xml_list.append(f'<row r="{r_idx}">{"".join(cell_xml_list)}</row>')

        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>
        {"".join(row_xml_list)}
    </sheetData>
</worksheet>"""

    @staticmethod
    def _col_to_letter(col: int) -> str:
        result = ""
        while col > 0:
            col, remainder = divmod(col - 1, 26)
            result = chr(65 + remainder) + result
        return result


def generate_excel_report(claim: ClaimData, audit: AuditReport, file_path: str):
    """Generates a complete Excel report (.xlsx) for the claim."""
    wb = OpenXLSXWriter()

    # --- SHEET 1: Summary & Audit ---
    s1_rows = [
        [{"val": f"CLAIM AUDIT REPORT: {claim.formatted_claim_ref}", "style": 2}],
        [{"val": f"Vehicle: {claim.formatted_vehicle} | Date: {claim.formatted_loss_date} | Mode: {claim.formatted_payment_mode}", "style": 0}],
        [],
        [{"val": f"OVERALL AUDIT STATUS: {audit.overall_status}", "style": 3}],
        [{"val": f"Identified {audit.total_mismatches_count} total mismatch discrepancies across data sources.", "style": 0}],
        [],
        # Section A: Claim Metadata
        [{"val": "CLAIM SUMMARY DETAILS", "style": 1}],
        [{"val": "Field Name", "style": 3}, {"val": "Field Value", "style": 7}],
        [{"val": "Claim Reference", "style": 7}, {"val": claim.formatted_claim_ref, "style": 7}],
        [{"val": "Vehicle Description", "style": 7}, {"val": claim.formatted_vehicle, "style": 7}],
        [{"val": "Date of Loss", "style": 7}, {"val": claim.formatted_loss_date, "style": 7}],
        [{"val": "Nature of Loss", "style": 7}, {"val": claim.formatted_nature_of_loss, "style": 7}],
        [{"val": "Payment Mode", "style": 7}, {"val": claim.formatted_payment_mode, "style": 7}],
        [{"val": "Vehicle Age Depreciation %", "style": 7}, {"val": format_percent(claim.parsed_estimate.vehicle_age_depreciation_pct), "style": 7}],
        [{"val": "Loss Summary", "style": 7}, {"val": claim.formatted_loss_summary, "style": 7}],
        [],
        # Section B: Totals Reconciliation Table
        [{"val": "RECONCILIATION OF TOTALS ACROSS DATA SOURCES", "style": 1}],
        [
            {"val": "Total Description", "style": 1},
            {"val": "Data Source", "style": 1},
            {"val": "Amount (INR)", "style": 1},
            {"val": "Audit Notes", "style": 1}
        ]
    ]

    for src in audit.sources_summary:
        amt_val = src.amount if src.amount is not None else NOT_AVAILABLE
        style = 4 if isinstance(amt_val, (int, float)) else 7
        s1_rows.append([
            {"val": src.label, "style": 7},
            {"val": src.source, "style": 7},
            {"val": amt_val, "style": style},
            {"val": src.notes, "style": 7}
        ])

    s1_rows.extend([
        [],
        # Section C: Audit Check Log
        [{"val": "AUDIT DISCREPANCY CHECK LOG", "style": 1}],
        [
            {"val": "Check ID", "style": 1},
            {"val": "Check Title", "style": 1},
            {"val": "Source A Label", "style": 1},
            {"val": "Value A (INR)", "style": 1},
            {"val": "Source B Label", "style": 1},
            {"val": "Value B (INR)", "style": 1},
            {"val": "Variance Amount", "style": 1},
            {"val": "Variance %", "style": 1},
            {"val": "Audit Status", "style": 1},
            {"val": "Detailed Explanation", "style": 1}
        ]
    ])

    for chk in audit.checks:
        status_style = 5 if chk.status == "MISMATCH" else (6 if chk.status == "MATCH" else 7)
        s1_rows.append([
            {"val": chk.check_id, "style": 7},
            {"val": chk.title, "style": 7},
            {"val": chk.source_a_label, "style": 7},
            {"val": chk.val_a if chk.val_a is not None else NOT_AVAILABLE, "style": 4 if isinstance(chk.val_a, (int, float)) else 7},
            {"val": chk.source_b_label, "style": 7},
            {"val": chk.val_b if chk.val_b is not None else NOT_AVAILABLE, "style": 4 if isinstance(chk.val_b, (int, float)) else 7},
            {"val": chk.diff_amount if chk.diff_amount is not None else NOT_AVAILABLE, "style": 4 if isinstance(chk.diff_amount, (int, float)) else 7},
            {"val": format_percent(chk.diff_percent) if chk.diff_percent is not None else NOT_AVAILABLE, "style": 7},
            {"val": chk.status, "style": status_style},
            {"val": chk.description, "style": 7}
        ])

    wb.add_sheet("Claim Summary & Audit", s1_rows)

    # --- SHEET 2: Estimate Line Items ---
    s2_rows = [
        [{"val": f"ITEMIZED ESTIMATE LINE ITEMS ({len(claim.parsed_estimate.lines)} Lines)", "style": 2}],
        [],
        [
            {"val": "Line #", "style": 1},
            {"val": "Part / Description", "style": 1},
            {"val": "Part Type", "style": 1},
            {"val": "Qty", "style": 1},
            {"val": "Stated Base Unit Amount (INR)", "style": 1},
            {"val": "Depreciation %", "style": 1},
            {"val": "GST %", "style": 1},
            {"val": "Calculated / Final Line Total (INR)", "style": 1}
        ]
    ]

    for idx, line in enumerate(claim.parsed_estimate.lines, 1):
        base_amt = line.part_total if line.part_total is not None else NOT_AVAILABLE
        final_amt = line.total_final_amt if line.total_final_amt is not None else line.calculated_final_amt
        final_val = final_amt if final_amt is not None else NOT_AVAILABLE

        s2_rows.append([
            {"val": idx, "style": 7},
            {"val": line.part_name, "style": 7},
            {"val": line.part_type, "style": 7},
            {"val": line.quantity, "style": 7},
            {"val": base_amt, "style": 4 if isinstance(base_amt, (int, float)) else 7},
            {"val": format_percent(line.part_dep_perc), "style": 7},
            {"val": format_percent(line.part_gst_perc), "style": 7},
            {"val": final_val, "style": 4 if isinstance(final_val, (int, float)) else 7}
        ])

    wb.add_sheet("Estimate Line Items", s2_rows)

    wb.save(file_path)
