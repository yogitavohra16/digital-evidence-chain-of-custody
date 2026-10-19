"""pdf_generator.py - builds the evidence PDF report with ReportLab.

WHAT IT DOES
    Takes real database records (case, evidence, custody events, latest verification,
    blockchain validation) and lays them out as a PDF in memory.

LAYOUT NOTES
    * Table cells are `Paragraph` objects, so text wraps inside the column instead of
      running off the page.
    * Hash cells use wordWrap="CJK", which lets ReportLab break a long unbroken
      string (like a 64-character hash) at any character.
    * Tables use `repeatRows=1` so the header repeats if a table spans pages.

DISCLAIMER: the report is a summary of the data in this prototype. It does not
guarantee, and must not be presented as proof of, legal admissibility.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


APP_NAME = "Blockchain-Based Digital Evidence Chain of Custody System"

# Forensic Violet palette
NAVY = colors.HexColor("#172554")
VIOLET = colors.HexColor("#6D28D9")
LAVENDER = colors.HexColor("#F5F3FF")
TEXT = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
SUCCESS = colors.HexColor("#15803D")
ERROR = colors.HexColor("#B91C1C")
WARNING = colors.HexColor("#B45309")


def _local(moment):
    """Format a datetime in the configured local time zone, e.g. '12 Oct 2026, 14:30:05'."""
    if moment is None:
        return "-"
    return timezone.localtime(moment).strftime("%d %b %Y, %H:%M:%S")


def _styles():
    """Create the paragraph styles used in the report."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], textColor=NAVY, fontSize=18, alignment=0, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], textColor=MUTED, fontSize=9),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=VIOLET, fontSize=12, spaceBefore=12, spaceAfter=5),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=11, textColor=TEXT),
        "cell_bold": ParagraphStyle("cell_bold", parent=base["Normal"], fontSize=8.5, leading=11, textColor=NAVY, fontName="Helvetica-Bold"),
        "hash": ParagraphStyle("hash", parent=base["Normal"], fontSize=7.5, leading=9.5, fontName="Courier", textColor=TEXT, wordWrap="CJK"),
        "head": ParagraphStyle("head", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold"),
        "note": ParagraphStyle("note", parent=base["Normal"], fontSize=8, leading=10.5, textColor=MUTED),
    }


def _p(text, style):
    """Make a Paragraph from plain text (escaping &, <, > so user text cannot break the PDF)."""
    return Paragraph(escape(str(text if text not in (None, "") else "-")), style)


def _key_value_table(rows, styles, width):
    """Two-column 'label: value' table. Returns a ReportLab Table."""
    data = [[_p(label, styles["cell_bold"]), value if hasattr(value, "wrap") else _p(value, styles["cell"])]
            for label, value in rows]
    table = Table(data, colWidths=[width * 0.28, width * 0.72])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), LAVENDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _header_footer(canvas, document):
    """Draw the top band and 'Page N' footer on every page."""
    canvas.saveState()
    page_width, page_height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_height - 12 * mm, page_width, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18 * mm, page_height - 7.5 * mm, "Evidence Chain of Custody Report")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 9 * mm, "Academic prototype - not a certified forensic tool. No claim of legal admissibility.")
    canvas.drawRightString(page_width - 18 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_evidence_report(evidence, events, latest_verification, chain_result, validated_at, generated_by):
    """Build the PDF and return it as bytes.

    Inputs:
        evidence            - Evidence object (with .case)
        events              - iterable of CustodyEvent (oldest first, with block_record)
        latest_verification - VerificationRecord or None
        chain_result        - ChainValidationResult for the whole blockchain
        validated_at        - datetime the chain validation was run
        generated_by        - the User generating the report
    Returns: bytes of the finished PDF.
    """
    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title=f"Custody report {evidence.evidence_id}", author=APP_NAME,
    )
    width = A4[0] - 36 * mm
    case = evidence.case
    story = [
        Paragraph(escape(APP_NAME), styles["title"]),
        Paragraph(f"Evidence report for {escape(evidence.evidence_id)} &nbsp;|&nbsp; generated "
                  f"{_local(timezone.now())} by {escape(generated_by.get_username())}", styles["subtitle"]),
    ]

    # --- Case ---
    story.append(Paragraph("1. Case details", styles["h2"]))
    story.append(_key_value_table([
        ("Case ID", case.case_id), ("Title", case.title), ("Status", case.get_status_display()),
        ("Description", case.description), ("Created", _local(case.created_at)),
    ], styles, width))

    # --- Evidence ---
    story.append(Paragraph("2. Evidence and registration", styles["h2"]))
    story.append(_key_value_table([
        ("Evidence ID", evidence.evidence_id), ("Original filename", evidence.original_filename),
        ("File type", evidence.file_extension.upper()), ("File size", f"{evidence.file_size:,} bytes"),
        ("Original SHA-256", Paragraph(escape(evidence.sha256_hash), styles["hash"])),
        ("Registered by", evidence.registered_by.get_username()),
        ("Registered at", _local(evidence.registered_at)),
        ("Current custody status", evidence.get_status_display()), ("Notes", evidence.notes),
    ], styles, width))

    # --- Custody history ---
    story.append(Paragraph("3. Chronological custody history", styles["h2"]))
    header = [_p(text, styles["head"]) for text in ("Time", "Action", "Performed by", "From > To", "Remarks", "Block", "Block hash")]
    rows = [header]
    for event in events:
        block = getattr(event, "block_record", None)
        route = f"{event.from_party or '-'} > {event.to_party or '-'}"
        rows.append([
            _p(_local(event.timestamp), styles["cell"]), _p(event.get_action_type_display(), styles["cell"]),
            _p(event.handler_name, styles["cell"]), _p(route, styles["cell"]), _p(event.remarks, styles["cell"]),
            _p(f"#{block.block_index}" if block else "none", styles["cell"]),
            Paragraph(escape(block.current_hash if block else "-"), styles["hash"]),
        ])
    fractions = [0.13, 0.13, 0.11, 0.12, 0.16, 0.06, 0.29]
    history = Table(rows, colWidths=[width * f for f in fractions], repeatRows=1)
    history.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LAVENDER]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(history)

    # --- Verification ---
    story.append(Paragraph("4. Latest evidence verification", styles["h2"]))
    if latest_verification is None:
        story.append(_p("No verification has been run for this evidence yet.", styles["cell"]))
    else:
        outcome = {"MATCH": "INTEGRITY VERIFIED", "MISMATCH": "INTEGRITY MISMATCH",
                   "FILE_MISSING": "FILE MISSING", "ERROR": "VERIFICATION ERROR"}[latest_verification.result]
        story.append(_key_value_table([
            ("Result", outcome), ("Verified at", _local(latest_verification.verified_at)),
            ("Verified by", latest_verification.verified_by.get_username()),
            ("Original SHA-256", Paragraph(escape(latest_verification.original_hash), styles["hash"])),
            ("Current SHA-256", Paragraph(escape(latest_verification.current_hash or "-"), styles["hash"])),
            ("Details", latest_verification.error_details),
        ], styles, width))
        story.append(Spacer(1, 3))
        story.append(_p("A mismatch means the file content differs from the registered version. "
                        "It does not by itself prove malicious tampering.", styles["note"]))

    # --- Blockchain validation ---
    story.append(Paragraph("5. Blockchain validation", styles["h2"]))
    verdict = "VALID" if chain_result.is_valid else "INVALID"
    story.append(_key_value_table([
        ("Validation result", verdict), ("Blocks checked", str(chain_result.total_blocks)),
        ("Validated at", _local(validated_at)), ("Summary", chain_result.message),
    ] + ([("Problems", "; ".join(chain_result.all_problems[:10]))] if not chain_result.is_valid else []),
        styles, width))

    # --- Disclaimer ---
    story.append(Paragraph("6. Important notes", styles["h2"]))
    story.append(_p(
        "This report summarises data held by a local academic prototype. A SHA-256 match shows only that file "
        "content is unchanged since registration; it does not prove origin or authenticity. The hash-linked ledger is "
        "tamper-evident, not tamper-proof, and a user-entered handler name does not independently prove identity. "
        "This report does not guarantee legal admissibility.", styles["note"]))

    document.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
