"""
pdf_generator.py - Standalone PDF Claim Report Generator

Generates a clean, professional multi-page PDF claim report natively in Python
following the PDF 1.4 specification (zero binary or external library dependencies).
Formats headers, metadata grids, source totals reconciliation tables, audit check logs,
and itemized estimate lines cleanly across pages.
"""

from typing import List, Tuple, Optional, Any
import os
from claim_parser import ClaimData, format_currency, format_percent, NOT_AVAILABLE
from audit_engine import AuditReport

class PDFCanvas:
    """Lightweight pure-Python PDF 1.4 canvas renderer."""

    def __init__(self, page_width: float = 595.28, page_height: float = 841.89): # A4
        self.width = page_width
        self.height = page_height
        self.pages_stream: List[List[str]] = []
        self.current_page: List[str] = []
        self.fonts = {"F1": "Helvetica", "F2": "Helvetica-Bold"}
        self._new_page()

    def _new_page(self):
        if self.current_page:
            self.pages_stream.append(self.current_page)
        self.current_page = []
        # Reset default color & state
        self.set_color(0.06, 0.09, 0.16) # #0f172a
        self.set_fill_color(1.0, 1.0, 1.0)

    def draw_rect(self, x: float, y: float, w: float, h: float, fill_rgb: Optional[Tuple[float, float, float]] = None, stroke_rgb: Optional[Tuple[float, float, float]] = None, stroke_width: float = 0.5):
        """Draws rectangle at (x, y) with width w and height h (y is distance from top of page)."""
        pdf_y = self.height - y - h
        cmd = []
        if stroke_rgb and stroke_width > 0:
            cmd.append(f"{stroke_width} w {stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
        if fill_rgb:
            cmd.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
            cmd.append(f"{x:.2f} {pdf_y:.2f} {w:.2f} {h:.2f} re f")
        if stroke_rgb and stroke_width > 0:
            cmd.append(f"{x:.2f} {pdf_y:.2f} {w:.2f} {h:.2f} re s")
        self.current_page.append("\n".join(cmd))

    def draw_text(self, text: str, x: float, y: float, font_key: str = "F1", size: float = 10, rgb: Tuple[float, float, float] = (0.1, 0.1, 0.1), align: str = "left"):
        """Draws text string at (x, y) top-left reference point."""
        if not text:
            return
        pdf_y = self.height - y - (size * 0.8) # Adjust baseline
        # Escape string for PDF
        escaped_text = (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("₹", "INR ")
        )
        
        # Approximate width for right alignment
        if align == "right":
            char_w = size * 0.52
            str_w = len(escaped_text) * char_w
            x = x - str_w
        elif align == "center":
            char_w = size * 0.52
            str_w = len(escaped_text) * char_w
            x = x - (str_w / 2.0)

        cmd = [
            f"BT",
            f"/{font_key} {size:.1f} Tf",
            f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg",
            f"1 0 0 1 {x:.2f} {pdf_y:.2f} Tm",
            f"({escaped_text}) Tj",
            f"ET"
        ]
        self.current_page.append("\n".join(cmd))

    def set_color(self, r: float, g: float, b: float):
        self.current_page.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def set_fill_color(self, r: float, g: float, b: float):
        self.current_page.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, rgb: Tuple[float, float, float] = (0.8, 0.8, 0.8), width: float = 0.5):
        pdf_y1 = self.height - y1
        pdf_y2 = self.height - y2
        cmd = f"{width} w {rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} RG {x1:.2f} {pdf_y1:.2f} m {x2:.2f} {pdf_y2:.2f} l S"
        self.current_page.append(cmd)

    def output(self) -> bytes:
        """Assembles PDF objects and returns binary string."""
        if self.current_page:
            self.pages_stream.append(self.current_page)

        objects = []
        # Obj 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # Obj 2: Pages list placeholder
        page_refs = " ".join(f"{i + 4} 0 R" for i in range(len(self.pages_stream)))
        objects.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(self.pages_stream)} >>".encode("ascii"))

        # Obj 3: Fonts definition
        fonts_def = (
            b"<< /Font << "
            b"/F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> "
            b"/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >> "
            b">> >>"
        )
        objects.append(fonts_def)

        # Page objects and stream objects
        content_obj_indices = []
        curr_obj_idx = 4
        for p_idx, stream_lines in enumerate(self.pages_stream):
            stream_content = "\n".join(stream_lines).encode("latin1", errors="replace")
            # Page dict obj
            page_dict = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] /Resources 3 0 R /Contents {curr_obj_idx + 1} 0 R >>".encode("ascii")
            objects.append(page_dict)
            
            # Stream obj
            stream_obj = f"<< /Length {len(stream_content)} >>\nstream\n".encode("ascii") + stream_content + b"\nendstream"
            objects.append(stream_obj)

            curr_obj_idx += 2

        # Build PDF xref table
        pdf_bytes = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []

        for obj_i, obj_body in enumerate(objects, 1):
            offsets.append(len(pdf_bytes))
            pdf_bytes.extend(f"{obj_i} 0 obj\n".encode("ascii"))
            pdf_bytes.extend(obj_body)
            pdf_bytes.extend(b"\nendobj\n")

        xref_start = len(pdf_bytes)
        pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
        for off in offsets:
            pdf_bytes.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        pdf_bytes.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii"))
        return bytes(pdf_bytes)


def generate_pdf_report(claim: ClaimData, audit: AuditReport, file_path: str):
    """Generates PDF claim report using native canvas renderer."""
    canvas = PDFCanvas(page_width=595.28, page_height=841.89) # A4
    margin = 36
    content_w = canvas.width - (margin * 2)

    cur_y = 36

    # --- Header Banner ---
    canvas.draw_rect(margin, cur_y, content_w, 65, fill_rgb=(0.12, 0.11, 0.29)) # Deep Navy
    canvas.draw_text(f"CLAIM AUDIT REPORT: {claim.formatted_claim_ref}", margin + 16, cur_y + 16, font_key="F2", size=16, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text(f"Vehicle: {claim.formatted_vehicle}  |  Date: {claim.formatted_loss_date}  |  Mode: {claim.formatted_payment_mode}", margin + 16, cur_y + 40, font_key="F1", size=9, rgb=(0.7, 0.75, 0.85))

    cur_y += 75

    # --- Status Alert Box ---
    is_critical = audit.total_mismatches_count > 0
    bg_color = (0.98, 0.9, 0.91) if is_critical else (0.88, 0.97, 0.92) # Soft Rose / Emerald
    stroke_color = (0.95, 0.25, 0.35) if is_critical else (0.06, 0.72, 0.5)
    status_text = f"AUDIT STATUS: {audit.overall_status}"
    sub_text = f"Identified {audit.total_mismatches_count} total mismatch discrepancies across data sources."

    canvas.draw_rect(margin, cur_y, content_w, 40, fill_rgb=bg_color, stroke_rgb=stroke_color, stroke_width=1)
    canvas.draw_text(status_text, margin + 14, cur_y + 10, font_key="F2", size=11, rgb=stroke_color)
    canvas.draw_text(sub_text, margin + 14, cur_y + 25, font_key="F1", size=9, rgb=(0.2, 0.2, 0.2))

    cur_y += 50

    # --- Claim Summary Metadata Grid ---
    canvas.draw_text("CLAIM SUMMARY DETAILS", margin, cur_y, font_key="F2", size=11, rgb=(0.06, 0.09, 0.16))
    canvas.draw_line(margin, cur_y + 14, margin + content_w, cur_y + 14, rgb=(0.2, 0.3, 0.4), width=1)
    cur_y += 20

    meta_items = [
        ("Claim Reference", claim.formatted_claim_ref),
        ("Vehicle", claim.formatted_vehicle),
        ("Date of Loss", claim.formatted_loss_date),
        ("Nature of Loss", claim.formatted_nature_of_loss),
        ("Payment Mode", claim.formatted_payment_mode),
        ("Age Depreciation", format_percent(claim.parsed_estimate.vehicle_age_depreciation_pct))
    ]

    col_w = content_w / 3.0
    for idx, (label, val) in enumerate(meta_items):
        row_i = idx // 3
        col_i = idx % 3
        cell_x = margin + (col_i * col_w)
        cell_y = cur_y + (row_i * 32)
        
        canvas.draw_rect(cell_x, cell_y, col_w - 6, 28, fill_rgb=(0.95, 0.96, 0.98), stroke_rgb=(0.85, 0.88, 0.92), stroke_width=0.5)
        canvas.draw_text(label.upper(), cell_x + 6, cell_y + 5, font_key="F1", size=7, rgb=(0.5, 0.55, 0.65))
        canvas.draw_text(val, cell_x + 6, cell_y + 15, font_key="F2", size=9, rgb=(0.1, 0.1, 0.1))

    cur_y += 75

    # Loss Summary Note
    canvas.draw_rect(margin, cur_y, content_w, 30, fill_rgb=(0.97, 0.98, 1.0), stroke_rgb=(0.85, 0.88, 0.92), stroke_width=0.5)
    canvas.draw_text("LOSS SUMMARY DESCRIPTION:", margin + 8, cur_y + 6, font_key="F2", size=7, rgb=(0.4, 0.45, 0.55))
    canvas.draw_text(claim.formatted_loss_summary, margin + 8, cur_y + 16, font_key="F1", size=8, rgb=(0.15, 0.15, 0.15))

    cur_y += 42

    # --- Section: Reconciliation of Totals Table ---
    canvas.draw_text("RECONCILIATION OF TOTALS ACROSS DATA SOURCES", margin, cur_y, font_key="F2", size=11, rgb=(0.06, 0.09, 0.16))
    canvas.draw_line(margin, cur_y + 14, margin + content_w, cur_y + 14, rgb=(0.2, 0.3, 0.4), width=1)
    cur_y += 20

    # Table Header
    canvas.draw_rect(margin, cur_y, content_w, 18, fill_rgb=(0.12, 0.16, 0.23))
    canvas.draw_text("TOTAL DESCRIPTION", margin + 8, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("DATA SOURCE", margin + 220, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("AMOUNT (INR)", margin + content_w - 8, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
    cur_y += 18

    for s_idx, src in enumerate(audit.sources_summary):
        bg = (0.97, 0.97, 0.98) if s_idx % 2 == 1 else (1.0, 1.0, 1.0)
        canvas.draw_rect(margin, cur_y, content_w, 18, fill_rgb=bg, stroke_rgb=(0.9, 0.9, 0.9), stroke_width=0.3)
        canvas.draw_text(src.label, margin + 8, cur_y + 4, font_key="F2", size=8, rgb=(0.1, 0.1, 0.1))
        canvas.draw_text(src.source, margin + 220, cur_y + 4, font_key="F1", size=8, rgb=(0.4, 0.4, 0.4))
        canvas.draw_text(src.formatted_amount, margin + content_w - 8, cur_y + 4, font_key="F2", size=8, rgb=(0.0, 0.4, 0.8), align="right")
        cur_y += 18

    cur_y += 15

    # --- Section: "Check" Discrepancy Log ---
    if cur_y + 120 > canvas.height - 40:
        canvas._new_page()
        cur_y = 36

    canvas.draw_text("CHECK SECTION - AUDIT DISCREPANCY LOG", margin, cur_y, font_key="F2", size=11, rgb=(0.06, 0.09, 0.16))
    canvas.draw_line(margin, cur_y + 14, margin + content_w, cur_y + 14, rgb=(0.2, 0.3, 0.4), width=1)
    cur_y += 20

    for chk in audit.checks:
        box_h = 36
        if cur_y + box_h > canvas.height - 40:
            canvas._new_page()
            cur_y = 36

        is_mismatch = chk.status == "MISMATCH"
        border_c = (0.95, 0.25, 0.35) if is_mismatch else (0.06, 0.72, 0.5)
        canvas.draw_rect(margin, cur_y, content_w, box_h, fill_rgb=(0.98, 0.98, 0.99), stroke_rgb=border_c, stroke_width=0.8)
        
        title_line = f"[{chk.check_id}] {chk.title}  --  STATUS: {chk.status}"
        canvas.draw_text(title_line, margin + 8, cur_y + 6, font_key="F2", size=9, rgb=border_c)
        
        # Truncate description for clean rendering in 1 line
        desc_line = chk.description
        if len(desc_line) > 105:
            desc_line = desc_line[:102] + "..."
        canvas.draw_text(desc_line, margin + 8, cur_y + 20, font_key="F1", size=8, rgb=(0.25, 0.25, 0.25))
        
        cur_y += box_h + 8

    cur_y += 15

    # --- Section: Itemized Estimate Lines Table ---
    if cur_y + 120 > canvas.height - 40:
        canvas._new_page()
        cur_y = 36

    canvas.draw_text(f"ITEMIZED ESTIMATE LINE ITEMS ({len(claim.parsed_estimate.lines)} Lines)", margin, cur_y, font_key="F2", size=11, rgb=(0.06, 0.09, 0.16))
    canvas.draw_line(margin, cur_y + 14, margin + content_w, cur_y + 14, rgb=(0.2, 0.3, 0.4), width=1)
    cur_y += 20

    # Table Headers
    canvas.draw_rect(margin, cur_y, content_w, 18, fill_rgb=(0.12, 0.16, 0.23))
    canvas.draw_text("#", margin + 6, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("PART / DESCRIPTION", margin + 28, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("TYPE", margin + 230, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("QTY", margin + 280, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
    canvas.draw_text("BASE UNIT (INR)", margin + 370, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
    canvas.draw_text("DEP %", margin + 420, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
    canvas.draw_text("GST %", margin + 465, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
    canvas.draw_text("TOTAL (INR)", margin + content_w - 6, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
    cur_y += 18

    for l_idx, line in enumerate(claim.parsed_estimate.lines, 1):
        if cur_y + 18 > canvas.height - 40:
            canvas._new_page()
            cur_y = 36
            # Repeat header on new page
            canvas.draw_rect(margin, cur_y, content_w, 18, fill_rgb=(0.12, 0.16, 0.23))
            canvas.draw_text("#", margin + 6, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
            canvas.draw_text("PART / DESCRIPTION", margin + 28, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
            canvas.draw_text("TYPE", margin + 230, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
            canvas.draw_text("QTY", margin + 280, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0))
            canvas.draw_text("BASE UNIT (INR)", margin + 370, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
            canvas.draw_text("DEP %", margin + 420, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
            canvas.draw_text("GST %", margin + 465, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
            canvas.draw_text("TOTAL (INR)", margin + content_w - 6, cur_y + 4, font_key="F2", size=8, rgb=(1.0, 1.0, 1.0), align="right")
            cur_y += 18

        bg = (0.97, 0.97, 0.98) if l_idx % 2 == 1 else (1.0, 1.0, 1.0)
        canvas.draw_rect(margin, cur_y, content_w, 16, fill_rgb=bg, stroke_rgb=(0.9, 0.9, 0.9), stroke_width=0.3)
        
        # Truncate long part names
        pname = line.part_name
        if len(pname) > 32:
            pname = pname[:30] + ".."

        canvas.draw_text(str(l_idx), margin + 6, cur_y + 3, font_key="F1", size=8, rgb=(0.4, 0.4, 0.4))
        canvas.draw_text(pname, margin + 28, cur_y + 3, font_key="F2", size=8, rgb=(0.1, 0.1, 0.1))
        canvas.draw_text(line.part_type, margin + 230, cur_y + 3, font_key="F1", size=8, rgb=(0.4, 0.4, 0.4))
        canvas.draw_text(str(line.quantity), margin + 280, cur_y + 3, font_key="F1", size=8, rgb=(0.1, 0.1, 0.1))
        canvas.draw_text(line.formatted_part_total, margin + 370, cur_y + 3, font_key="F1", size=8, rgb=(0.2, 0.2, 0.2), align="right")
        canvas.draw_text(line.formatted_dep_perc, margin + 420, cur_y + 3, font_key="F1", size=8, rgb=(0.2, 0.2, 0.2), align="right")
        canvas.draw_text(line.formatted_gst_perc, margin + 465, cur_y + 3, font_key="F1", size=8, rgb=(0.2, 0.2, 0.2), align="right")
        canvas.draw_text(line.formatted_final_amt, margin + content_w - 6, cur_y + 3, font_key="F2", size=8, rgb=(0.0, 0.5, 0.3), align="right")
        cur_y += 16

    # Write PDF file out
    pdf_bytes = canvas.output()
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
