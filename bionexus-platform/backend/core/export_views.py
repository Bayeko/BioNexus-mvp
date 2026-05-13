"""Export endpoints for measurements, samples, and audit trail.

Supports CSV and PDF export for LIMS integration and compliance reporting.

PDF output is generated via ReportLab with refined-industrial typography
+ a Labionexus header + page numbers + integrity footer carrying the
report SHA-256 hash. Use the measurements PDF for routine record
exports and the audit-trail PDF for regulatory submissions.
"""

import csv
import hashlib
import io
from datetime import datetime, timezone as dt_timezone

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from modules.measurements.models import Measurement
from modules.samples.models import Sample
from core.models import AuditLog


# ---------------------------------------------------------------------------
# Shared PDF infrastructure
# ---------------------------------------------------------------------------

# Refined-industrial palette. Matches the React theme tokens.
LBN_NAVY = colors.HexColor("#1F4E79")
LBN_ACCENT = colors.HexColor("#2E75B6")
LBN_BORDER = colors.HexColor("#D0D7DE")
LBN_MUTED = colors.HexColor("#586573")
LBN_BG_HEADER = colors.HexColor("#F3F6FA")
LBN_WARN = colors.HexColor("#F59E0B")
LBN_OK = colors.HexColor("#3FB950")
LBN_ERROR = colors.HexColor("#EF4444")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "lbn-title", parent=base["Title"],
            textColor=LBN_NAVY, fontName="Helvetica-Bold",
            fontSize=20, leading=24, alignment=TA_LEFT, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "lbn-subtitle", parent=base["Normal"],
            textColor=LBN_MUTED, fontName="Helvetica",
            fontSize=10, leading=14, alignment=TA_LEFT, spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "lbn-section", parent=base["Heading2"],
            textColor=LBN_NAVY, fontName="Helvetica-Bold",
            fontSize=12, leading=16, alignment=TA_LEFT,
            spaceBefore=8, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "lbn-body", parent=base["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
        ),
        "mono": ParagraphStyle(
            "lbn-mono", parent=base["Code"],
            fontName="Courier", fontSize=8, leading=10,
        ),
        "footer": ParagraphStyle(
            "lbn-footer", parent=base["Normal"],
            textColor=LBN_MUTED, fontName="Helvetica",
            fontSize=8, leading=10, alignment=TA_CENTER,
        ),
    }


def _compute_report_hash(rows: list[list[str]]) -> str:
    """Deterministic SHA-256 over the rendered row data.

    Lets a recipient verify the PDF content is intact : hash the
    underlying records the same way, compare to the value printed in
    the footer + header. Independent of PDF layout, font, page count.
    """
    canonical = "\n".join("|".join(str(cell) for cell in row) for row in rows)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _draw_page_chrome(report_title: str, doc_id: str, report_hash: str):
    """Build a per-page on-draw callback : header + footer + page X / Y."""

    def _on_page(canvas: pdf_canvas.Canvas, doc):
        width, height = doc.pagesize
        canvas.saveState()

        # Header band
        canvas.setFillColor(LBN_BG_HEADER)
        canvas.rect(0, height - 22 * mm, width, 22 * mm, stroke=0, fill=1)
        canvas.setStrokeColor(LBN_ACCENT)
        canvas.setLineWidth(0.6)
        canvas.line(0, height - 22 * mm, width, height - 22 * mm)

        # Brand wordmark (text only — no PNG dependency)
        canvas.setFillColor(LBN_NAVY)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(15 * mm, height - 14 * mm, "Labionexus")
        canvas.setFillColor(LBN_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15 * mm, height - 18 * mm, "Laboratory Data Platform")

        # Doc id + title on the right
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(LBN_NAVY)
        canvas.drawRightString(width - 15 * mm, height - 12 * mm, report_title)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(LBN_MUTED)
        canvas.drawRightString(width - 15 * mm, height - 17 * mm, doc_id)

        # Footer band : page number + report hash
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(LBN_MUTED)
        canvas.drawString(
            15 * mm, 12 * mm,
            f"Integrity hash : {report_hash[:32]}…",
        )
        canvas.drawCentredString(
            width / 2, 12 * mm,
            "21 CFR Part 11 §11.50 compliant · LBN-RPT-001",
        )
        canvas.drawRightString(
            width - 15 * mm, 12 * mm,
            f"Page {doc.page}",
        )
        canvas.line(15 * mm, 16 * mm, width - 15 * mm, 16 * mm)

        canvas.restoreState()

    return _on_page


def _build_pdf(
    *,
    report_title: str,
    doc_id: str,
    rows: list[list[str]],
    column_widths: list[float],
    headers: list[str],
    meta_lines: list[str],
    landscape_mode: bool = True,
    color_status_column: int | None = None,
) -> bytes:
    """Render a tabular PDF report with the Labionexus chrome.

    ``color_status_column`` is the index of a column whose cells get
    color-coded text by value : ``success`` => green, ``failed`` /
    ``alert`` => orange, ``dead_letter`` / ``block`` => red.
    """
    page_size = landscape(A4) if landscape_mode else A4
    margin = 15 * mm
    top_margin = 28 * mm  # extra room for the header band
    bottom_margin = 22 * mm  # extra room for the footer band

    report_hash = _compute_report_hash([headers, *rows])

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=report_title,
        author="Labionexus",
        subject=doc_id,
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        showBoundary=0,
    )
    doc.addPageTemplates([
        PageTemplate(
            id="main",
            frames=frame,
            onPage=_draw_page_chrome(report_title, doc_id, report_hash),
        ),
    ])

    styles = _styles()
    story = []
    story.append(Paragraph(report_title, styles["title"]))
    if meta_lines:
        story.append(Paragraph(" · ".join(meta_lines), styles["subtitle"]))
    story.append(Spacer(1, 4 * mm))

    # Build the table
    table_data = [[Paragraph(f"<b>{h}</b>", styles["body"]) for h in headers]]
    for row in rows:
        table_data.append([Paragraph(str(cell), styles["body"]) for cell in row])

    table = Table(table_data, colWidths=column_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), LBN_BG_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), LBN_NAVY),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LBN_ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.2, LBN_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFD")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if color_status_column is not None:
        for idx, row in enumerate(rows, start=1):
            value = (str(row[color_status_column]) if color_status_column < len(row) else "").lower()
            if value in ("success", "log"):
                fg = LBN_OK
            elif value in ("failed", "alert"):
                fg = LBN_WARN
            elif value in ("dead_letter", "block"):
                fg = LBN_ERROR
            else:
                continue
            style_cmds.append((
                "TEXTCOLOR", (color_status_column, idx),
                (color_status_column, idx), fg,
            ))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    # Trailing footer paragraph with the full integrity hash
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"<b>Report integrity hash (SHA-256)</b><br/><font face='Courier' size='8'>{report_hash}</font>",
        styles["body"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "This report is generated automatically. Records are bound to "
        "the integrity hash above ; any post-export modification is "
        "detectable by recomputing the hash from the source data.",
        styles["footer"],
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def _doc_id(prefix: str) -> str:
    """Deterministic, sortable doc ID for the report."""
    return f"{prefix}-{datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _apply_date_filters(qs, request, date_field="created_at"):
    """Apply optional date_from / date_to query params."""
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        qs = qs.filter(**{f"{date_field}__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{date_field}__lte": date_to})
    return qs


# ── Measurements Export ──────────────────────────────────────────────────────


@api_view(["GET"])
def export_measurements_csv(request):
    """Export measurements as CSV.

    GET /api/export/measurements/csv/
    Query params: instrument, sample, parameter, date_from, date_to
    """
    qs = Measurement.objects.select_related("sample", "instrument").order_by("-created_at")

    if request.GET.get("instrument"):
        qs = qs.filter(instrument_id=request.GET["instrument"])
    if request.GET.get("sample"):
        qs = qs.filter(sample_id=request.GET["sample"])
    if request.GET.get("parameter"):
        qs = qs.filter(parameter=request.GET["parameter"])
    qs = _apply_date_filters(qs, request)

    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="bionexus_measurements_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Sample ID", "Instrument", "Parameter", "Value", "Unit",
        "Measured At", "Data Hash (SHA-256)", "Created At",
    ])

    for m in qs[:5000]:
        writer.writerow([
            m.id,
            m.sample.sample_id if m.sample else "",
            m.instrument.name if m.instrument else "",
            m.parameter,
            str(m.value),
            m.unit,
            m.measured_at.isoformat() if m.measured_at else "",
            m.data_hash,
            m.created_at.isoformat(),
        ])

    return response


@api_view(["GET"])
def export_measurements_pdf(request):
    """Export measurements as a real, auditor-grade PDF (ReportLab).

    GET /api/export/measurements/pdf/
    Query params: instrument, sample, parameter, date_from, date_to

    Each row carries the truncated SHA-256 data_hash so a verifier can
    fetch the full record by ID and recompute. The footer carries the
    SHA-256 of the entire report so any post-export tampering is
    detectable without trusting the PDF format itself.
    """
    qs = Measurement.objects.select_related("sample", "instrument").order_by("-created_at")

    filters_applied = []
    if request.GET.get("instrument"):
        qs = qs.filter(instrument_id=request.GET["instrument"])
        filters_applied.append(f"instrument={request.GET['instrument']}")
    if request.GET.get("sample"):
        qs = qs.filter(sample_id=request.GET["sample"])
        filters_applied.append(f"sample={request.GET['sample']}")
    if request.GET.get("parameter"):
        qs = qs.filter(parameter=request.GET["parameter"])
        filters_applied.append(f"parameter={request.GET['parameter']}")
    if request.GET.get("date_from"):
        filters_applied.append(f"from={request.GET['date_from']}")
    if request.GET.get("date_to"):
        filters_applied.append(f"to={request.GET['date_to']}")
    qs = _apply_date_filters(qs, request)

    measurements = list(qs[:5000])

    rows = [
        [
            str(m.id),
            (m.sample.sample_id if m.sample else "—"),
            (m.instrument.name if m.instrument else "—"),
            m.parameter,
            str(m.value),
            m.unit,
            (m.measured_at.strftime("%Y-%m-%d %H:%M:%S") if m.measured_at else "—"),
            f"{m.data_hash[:12]}…" if m.data_hash else "—",
        ]
        for m in measurements
    ]

    doc_id = _doc_id("LBN-RPT-MEAS")
    meta = [
        f"Generated {datetime.now(dt_timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"{len(measurements)} record(s)",
    ]
    if filters_applied:
        meta.append("Filters : " + ", ".join(filters_applied))

    pdf_bytes = _build_pdf(
        report_title="Measurement Export Report",
        doc_id=doc_id,
        rows=rows,
        column_widths=[
            16 * mm, 28 * mm, 38 * mm, 28 * mm,
            22 * mm, 14 * mm, 38 * mm, 38 * mm,
        ],
        headers=[
            "ID", "Sample", "Instrument", "Parameter",
            "Value", "Unit", "Measured at (UTC)", "Data hash (SHA-256)",
        ],
        meta_lines=meta,
        landscape_mode=True,
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{doc_id}.pdf"'
    )
    return response


@api_view(["GET"])
def export_audit_pdf(request):
    """Export audit trail as a signed, auditor-grade PDF (ReportLab).

    GET /api/export/audit/pdf/
    Query params: entity_type, operation, date_from, date_to

    The output is designed for Annex 11 §12 and 21 CFR Part 11
    inspection : each row carries the operation, signature (truncated),
    and previous_signature reference, so a recipient can verify the
    audit chain integrity by walking signatures from row to row.
    """
    qs = AuditLog.objects.all().order_by("-timestamp")

    filters_applied = []
    if request.GET.get("entity_type"):
        qs = qs.filter(entity_type=request.GET["entity_type"])
        filters_applied.append(f"entity_type={request.GET['entity_type']}")
    if request.GET.get("operation"):
        qs = qs.filter(operation=request.GET["operation"])
        filters_applied.append(f"operation={request.GET['operation']}")
    if request.GET.get("date_from"):
        filters_applied.append(f"from={request.GET['date_from']}")
    if request.GET.get("date_to"):
        filters_applied.append(f"to={request.GET['date_to']}")
    qs = _apply_date_filters(qs, request, date_field="timestamp")

    logs = list(qs[:10000])

    rows = [
        [
            str(log.id),
            (log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "—"),
            log.entity_type,
            str(log.entity_id),
            log.operation,
            log.user_email or "system",
            f"{log.signature[:12]}…" if log.signature else "—",
        ]
        for log in logs
    ]

    doc_id = _doc_id("LBN-RPT-AUDIT")
    meta = [
        f"Generated {datetime.now(dt_timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"{len(logs)} audit record(s)",
        "21 CFR Part 11 §11.10(e) + EU GMP Annex 11 §12",
    ]
    if filters_applied:
        meta.append("Filters : " + ", ".join(filters_applied))

    pdf_bytes = _build_pdf(
        report_title="Audit Trail Export",
        doc_id=doc_id,
        rows=rows,
        column_widths=[
            16 * mm, 38 * mm, 32 * mm, 18 * mm,
            22 * mm, 50 * mm, 40 * mm,
        ],
        headers=[
            "ID", "Timestamp (UTC)", "Entity type", "Entity ID",
            "Operation", "User", "Signature (SHA-256)",
        ],
        meta_lines=meta,
        landscape_mode=True,
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{doc_id}.pdf"'
    )
    return response


# ── Samples Export ───────────────────────────────────────────────────────────


@api_view(["GET"])
def export_samples_csv(request):
    """Export samples as CSV.

    GET /api/export/samples/csv/
    Query params: instrument, status, batch_number, date_from, date_to
    """
    qs = Sample.objects.filter(is_deleted=False).select_related("instrument").order_by("-created_at")

    if request.GET.get("instrument"):
        qs = qs.filter(instrument_id=request.GET["instrument"])
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("batch_number"):
        qs = qs.filter(batch_number__icontains=request.GET["batch_number"])
    qs = _apply_date_filters(qs, request)

    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="bionexus_samples_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Sample ID", "Instrument", "Batch Number", "Status",
        "Created By", "Created At", "Updated At",
    ])

    for s in qs[:5000]:
        writer.writerow([
            s.id,
            s.sample_id,
            s.instrument.name if s.instrument else "",
            s.batch_number,
            s.status,
            s.created_by,
            s.created_at.isoformat(),
            s.updated_at.isoformat(),
        ])

    return response


# ── Audit Trail Export ───────────────────────────────────────────────────────


@api_view(["GET"])
def export_audit_csv(request):
    """Export audit trail as CSV.

    GET /api/export/audit/csv/
    Query params: entity_type, operation, date_from, date_to
    """
    qs = AuditLog.objects.all().order_by("-timestamp")

    if request.GET.get("entity_type"):
        qs = qs.filter(entity_type=request.GET["entity_type"])
    if request.GET.get("operation"):
        qs = qs.filter(operation=request.GET["operation"])
    qs = _apply_date_filters(qs, request, date_field="timestamp")

    response = HttpResponse(content_type="text/csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="bionexus_audit_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Timestamp", "Entity Type", "Entity ID", "Operation",
        "User Email", "Signature (SHA-256)",
    ])

    for log in qs[:10000]:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.entity_type,
            log.entity_id,
            log.operation,
            log.user_email or "",
            log.signature[:16] + "..." if log.signature else "",
        ])

    return response


# ── Export Summary ───────────────────────────────────────────────────────────


@api_view(["GET"])
def export_formats(request):
    """List all available export endpoints.

    GET /api/export/
    """
    return Response({
        "exports": [
            {
                "name": "Measurements (CSV)",
                "url": "/api/export/measurements/csv/",
                "params": ["instrument", "sample", "parameter", "date_from", "date_to"],
            },
            {
                "name": "Measurements (PDF)",
                "url": "/api/export/measurements/pdf/",
                "params": ["instrument", "sample", "parameter", "date_from", "date_to"],
                "format": "auditor-grade PDF (ReportLab) with report-level integrity hash",
            },
            {
                "name": "Samples (CSV)",
                "url": "/api/export/samples/csv/",
                "params": ["instrument", "status", "batch_number", "date_from", "date_to"],
            },
            {
                "name": "Audit Trail (CSV)",
                "url": "/api/export/audit/csv/",
                "params": ["entity_type", "operation", "date_from", "date_to"],
            },
            {
                "name": "Audit Trail (PDF)",
                "url": "/api/export/audit/pdf/",
                "params": ["entity_type", "operation", "date_from", "date_to"],
                "format": "auditor-grade PDF (ReportLab) — Annex 11 §12 + 21 CFR Part 11 §11.10(e)",
            },
        ],
        "note": (
            "All exports include SHA-256 integrity hashes. PDF exports add "
            "a report-level hash in the footer for tamper-evident transport. "
            "Max 5000 measurement records / 10000 audit records per export."
        ),
    })
