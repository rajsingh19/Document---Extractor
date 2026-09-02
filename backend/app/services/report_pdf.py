"""
services/report_pdf.py — Deterministic PDF Renderer for Evidence Reports (Step 11F).

Consumes a ReportData object and produces a ReportLab PDF.
This renderer NEVER queries the database independently.
All data comes from the ReportData passed in — ensuring the PDF is
always identical to the API/frontend preview.

Architecture:
  ReportData (from EvidenceReportService)
      ↓
  ReportPDFRenderer.render(report_data) → bytes (PDF)

PDF Structure:
  Page 1: Header, Metadata, Executive Summary, Key Metrics
  Page 2: Emissions Summary, Evidence & Sources
  Page 3: Data Quality, Missing / Not Reported Data, Insights, Recommendations
  Final: Source Document Reference
"""
import io
import logging
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import (
    HexColor, black, white, lightgrey
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable

from backend.app.schemas.report import ReportData, ReportMetric, ReportEmissions

logger = logging.getLogger("senseible-report-pdf")

# ── Colour palette (clean, professional, B2B) ──────────────────────────────
C_BRAND_DARK   = HexColor("#0F172A")   # slate-900
C_BRAND_MED    = HexColor("#1E3A5F")   # blue-900
C_BRAND_BLUE   = HexColor("#2563EB")   # blue-600
C_ACCENT       = HexColor("#0EA5E9")   # sky-500
C_SLATE_700    = HexColor("#334155")
C_SLATE_500    = HexColor("#64748B")
C_SLATE_200    = HexColor("#E2E8F0")
C_SLATE_100    = HexColor("#F1F5F9")
C_WHITE        = HexColor("#FFFFFF")
C_GREEN        = HexColor("#16A34A")
C_AMBER        = HexColor("#D97706")
C_RED          = HexColor("#DC2626")
C_TABLE_HEADER = HexColor("#1E3A5F")
C_TABLE_ALT    = HexColor("#F8FAFC")

W, H = A4
L_MARGIN = R_MARGIN = 18 * mm
T_MARGIN = B_MARGIN = 18 * mm
CONTENT_W = W - L_MARGIN - R_MARGIN

# ── Style helpers ──────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=C_BRAND_DARK,
        spaceAfter=2,
        leading=28,
    )
    styles["subtitle"] = ParagraphStyle(
        "ReportSubtitle",
        fontName="Helvetica",
        fontSize=13,
        textColor=C_BRAND_MED,
        spaceAfter=2,
        leading=18,
    )
    styles["section_header"] = ParagraphStyle(
        "SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=C_BRAND_DARK,
        spaceBefore=14,
        spaceAfter=4,
        borderPad=4,
        leading=15,
    )
    styles["body"] = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=9,
        textColor=C_SLATE_700,
        leading=13,
        spaceAfter=2,
    )
    styles["small"] = ParagraphStyle(
        "Small",
        fontName="Helvetica",
        fontSize=8,
        textColor=C_SLATE_500,
        leading=11,
        spaceAfter=1,
    )
    styles["label"] = ParagraphStyle(
        "Label",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=C_SLATE_500,
        leading=12,
    )
    styles["value"] = ParagraphStyle(
        "Value",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=C_BRAND_DARK,
        leading=14,
    )
    styles["badge_green"] = ParagraphStyle(
        "BadgeGreen",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=C_GREEN,
    )
    styles["badge_amber"] = ParagraphStyle(
        "BadgeAmber",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=C_AMBER,
    )
    styles["badge_red"] = ParagraphStyle(
        "BadgeRed",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=C_RED,
    )
    styles["caption"] = ParagraphStyle(
        "Caption",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=C_SLATE_500,
        leading=11,
    )
    return styles


def _hr(color=C_SLATE_200, thickness=0.5, space_before=4, space_after=4):
    return HRFlowable(
        width="100%",
        thickness=thickness,
        color=color,
        spaceAfter=space_after,
        spaceBefore=space_before,
    )


def _table_style(has_header=True):
    cmds = [
        ("BACKGROUND",   (0, 0), (-1, 0 if has_header else -1), C_TABLE_HEADER if has_header else C_WHITE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE if has_header else C_BRAND_DARK),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_TABLE_ALT]),
        ("TEXTCOLOR",    (0, 1), (-1, -1), C_SLATE_700),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID",         (0, 0), (-1, -1), 0.3, C_SLATE_200),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]
    return TableStyle(cmds)


def _header_table_style():
    cmds = [
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",     (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 0), (0, -1), C_SLATE_500),
        ("TEXTCOLOR",    (1, 0), (1, -1), C_BRAND_DARK),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]
    return TableStyle(cmds)


def _format_val(v: float, unit: str) -> str:
    """Format a metric value cleanly for display."""
    if unit.lower() in ("kwh", "kl", "liters", "l", "kg"):
        return f"{v:,.0f}"
    if unit.lower() in ("tco2e",):
        return f"{v:.2f}"
    if unit.lower() in ("kva", "kw"):
        return f"{v:.2f}"
    if unit.lower() in ("pf",):
        return f"{v:.2f}"
    if unit.lower() in ("inr", "₹", "rs"):
        return f"{v:,.2f}"
    return f"{v:g}"


class ReportPDFRenderer:
    """
    Renders a ReportData to a PDF byte string using ReportLab.
    Consumes the ReportData passed to render() — no database access.
    """

    def render(self, report_data: ReportData) -> bytes:
        """Return the PDF as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=L_MARGIN,
            rightMargin=R_MARGIN,
            topMargin=T_MARGIN,
            bottomMargin=B_MARGIN,
            title="Sustainability Evidence Report",
            author="Senseible Document AI",
        )

        st = _styles()
        story = []

        # ── PAGE 1 ──────────────────────────────────────────────────────────
        story += self._cover_header(report_data, st)
        story += self._metadata_block(report_data, st)
        story += self._executive_summary_block(report_data, st)
        story += self._key_metrics_block(report_data, st)

        # ── PAGE 2 ──────────────────────────────────────────────────────────
        story.append(PageBreak())
        story += self._emissions_block(report_data, st)
        story += self._evidence_block(report_data, st)

        # ── PAGE 3 ──────────────────────────────────────────────────────────
        story.append(PageBreak())
        story += self._data_quality_block(report_data, st)
        story += self._missing_data_block(report_data, st)
        story += self._insights_block(report_data, st)
        story += self._recommendations_block(report_data, st)
        story += self._source_reference_block(report_data, st)

        doc.build(story, onFirstPage=self._on_page, onLaterPages=self._on_page)
        return buffer.getvalue()

    def _on_page(self, canvas, doc):
        """Add footer to every page."""
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_SLATE_500)
        canvas.drawString(
            L_MARGIN, 12 * mm,
            "Senseible Document AI — Sustainability Evidence Report — Confidential"
        )
        canvas.drawRightString(
            W - R_MARGIN, 12 * mm,
            f"Page {doc.page}"
        )
        canvas.restoreState()

    # ── Section builders ────────────────────────────────────────────────────

    def _cover_header(self, r: ReportData, st: dict) -> list:
        meta = r.metadata
        story = []
        story.append(Paragraph("SUSTAINABILITY EVIDENCE REPORT", st["title"]))
        company = meta.company_name or "Not available"
        period  = meta.reporting_period or "Not available"
        story.append(Paragraph(company, st["subtitle"]))
        story.append(Paragraph(f"Reporting Period: {period}", st["body"]))
        story.append(Spacer(1, 3 * mm))
        story.append(_hr(C_BRAND_BLUE, thickness=1.5))
        story.append(Spacer(1, 3 * mm))
        return story

    def _metadata_block(self, r: ReportData, st: dict) -> list:
        meta = r.metadata
        story = []
        vs = meta.verification_status or "Unknown"
        qs = f"{meta.quality_score:.0f}/100" if meta.quality_score is not None else "N/A"

        data = [
            ["Company",              meta.company_name or "Not available"],
            ["Document",             meta.document_name],
            ["Document Type",        meta.document_type or "Not classified"],
            ["Reporting Period",     meta.reporting_period or "Not available"],
            ["Verification Status",  vs],
            ["Quality Score",        qs],
            ["Generated",            meta.generated_at[:19].replace("T", " ") + " UTC"],
        ]
        tbl = Table(data, colWidths=[45 * mm, CONTENT_W - 45 * mm])
        tbl.setStyle(_header_table_style())
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))
        return story

    def _executive_summary_block(self, r: ReportData, st: dict) -> list:
        if not r.executive_summary:
            return []
        story = []
        story.append(Paragraph("EXECUTIVE SUMMARY", st["section_header"]))
        story.append(_hr())
        story.append(Paragraph(r.executive_summary, st["body"]))
        story.append(Spacer(1, 4 * mm))
        return story

    def _key_metrics_block(self, r: ReportData, st: dict) -> list:
        if not r.metrics:
            return []
        story = []
        story.append(Paragraph("KEY METRICS", st["section_header"]))
        story.append(_hr())

        headers = ["Metric", "Value", "Unit", "Period", "Status"]
        col_w = [55 * mm, 28 * mm, 22 * mm, 35 * mm, 30 * mm]

        rows = [headers]
        for m in r.metrics:
            if m.metric_type in ("scope_1_emissions", "scope_2_emissions", "total_ghg_emissions"):
                continue  # shown in emissions section
            rows.append([
                m.metric_name,
                _format_val(m.value, m.unit),
                m.unit,
                m.reporting_period or "—",
                m.verification_status or "—",
            ])

        if len(rows) == 1:
            story.append(Paragraph("No key metrics available.", st["body"]))
        else:
            tbl = Table(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(_table_style(has_header=True))
            story.append(tbl)

        story.append(Spacer(1, 4 * mm))
        return story

    def _emissions_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("EMISSIONS SUMMARY", st["section_header"]))
        story.append(_hr())

        em = r.emissions
        if not em.emissions_available:
            story.append(Paragraph(
                "Emissions data was not available in the selected document.",
                st["body"]
            ))
        else:
            rows = [["Scope", "Value", "Unit", "Source"]]
            if em.scope_1 is not None:
                rows.append([
                    "Scope 1 (Direct)",
                    f"{em.scope_1:.2f}",
                    em.scope_1_unit,
                    em.scope_1_source or "Source text unavailable.",
                ])
            if em.scope_2 is not None:
                rows.append([
                    "Scope 2 (Indirect — Grid)",
                    f"{em.scope_2:.2f}",
                    em.scope_2_unit,
                    em.scope_2_source or "Source text unavailable.",
                ])
            if em.total_ghg is not None:
                rows.append([
                    "Total GHG",
                    f"{em.total_ghg:.2f}",
                    em.total_ghg_unit,
                    em.total_ghg_source or "Source text unavailable.",
                ])

            col_w = [50 * mm, 22 * mm, 18 * mm, CONTENT_W - 90 * mm]
            tbl = Table(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(_table_style(has_header=True))
            story.append(tbl)

            if em.dominant_scope == "scope_2":
                story.append(Spacer(1, 2 * mm))
                story.append(Paragraph(
                    "Scope 2 (grid electricity) is the larger documented emissions category.",
                    st["caption"]
                ))
            elif em.dominant_scope == "scope_1":
                story.append(Spacer(1, 2 * mm))
                story.append(Paragraph(
                    "Scope 1 (direct fuel combustion) is the larger documented emissions category.",
                    st["caption"]
                ))

        story.append(Spacer(1, 4 * mm))
        return story

    def _evidence_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("EVIDENCE & SOURCES", st["section_header"]))
        story.append(_hr())

        if not r.evidence:
            story.append(Paragraph("No supporting evidence available.", st["body"]))
        else:
            rows = [["Metric", "Value", "Unit", "Source Text"]]
            for ev in r.evidence:
                val_str = _format_val(ev.value, ev.unit) if ev.value is not None else "—"
                src = ev.source_text or "Source text unavailable."
                # Truncate very long source text
                if len(src) > 120:
                    src = src[:117] + "..."
                rows.append([ev.metric_name, val_str, ev.unit or "—", src])

            col_w = [42 * mm, 20 * mm, 15 * mm, CONTENT_W - 77 * mm]
            tbl = Table(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(_table_style(has_header=True))
            story.append(tbl)

        story.append(Spacer(1, 4 * mm))
        return story

    def _data_quality_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("DATA QUALITY", st["section_header"]))
        story.append(_hr())

        dq = r.data_quality
        vs = dq.verification_status or "Unknown"
        qs = f"{dq.quality_score:.0f}/100" if dq.quality_score is not None else "N/A"

        data = [
            ["Verification Status",    vs],
            ["Quality Score",          qs],
            ["Extraction Method",      dq.extraction_method or "Not recorded"],
            ["Total Metrics Extracted", str(dq.metric_count)],
            ["AI Extracted",           str(dq.ai_extracted_metric_count)],
            ["Human Verified",         str(dq.verified_metric_count)],
        ]
        if dq.review_reasons:
            data.append(["Review Reasons", "; ".join(dq.review_reasons[:3])])

        tbl = Table(data, colWidths=[55 * mm, CONTENT_W - 55 * mm])
        tbl.setStyle(_header_table_style())
        story.append(tbl)

        if r.attention_flags:
            story.append(Spacer(1, 2 * mm))
            for flag in r.attention_flags:
                story.append(Paragraph(f"⚠ {flag}", st["small"]))

        story.append(Spacer(1, 4 * mm))
        return story

    def _missing_data_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("DATA NOT REPORTED", st["section_header"]))
        story.append(_hr())

        if not r.missing_data:
            story.append(Paragraph(
                "All tracked metric types are present in this document.", st["body"]
            ))
        else:
            rows = [["Field", "Status", "Note"]]
            for f in r.missing_data:
                status = "Not Applicable" if f.is_not_applicable else "Not Reported"
                rows.append([f.display_name, status, f.reason])

            col_w = [60 * mm, 30 * mm, CONTENT_W - 90 * mm]
            tbl = Table(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(_table_style(has_header=True))
            story.append(tbl)
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                "Note: 'Not Reported' means the field was absent from the document. "
                "Missing values are never treated as zero.",
                st["caption"]
            ))

        story.append(Spacer(1, 4 * mm))
        return story

    def _insights_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("INSIGHTS", st["section_header"]))
        story.append(_hr())

        if not r.insights:
            story.append(Paragraph(
                "No deterministic insights are available for this reporting period.",
                st["body"]
            ))
        else:
            for ins in r.insights:
                sev_style = {
                    "ATTENTION": st["badge_amber"],
                    "REVIEW": st["badge_red"],
                    "INFO": st["badge_green"],
                }.get(ins.severity, st["badge_green"])
                row = [
                    [
                        Paragraph(f"[{ins.severity}]", sev_style),
                        Paragraph(ins.title, st["label"]),
                        Paragraph(ins.message, st["body"]),
                    ]
                ]
                tbl = Table([[
                    Paragraph(f"[{ins.severity}]", sev_style),
                    Paragraph(ins.message, st["body"]),
                ]], colWidths=[20 * mm, CONTENT_W - 20 * mm])
                tbl.setStyle(TableStyle([
                    ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING",   (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(KeepTogether([tbl, Spacer(1, 1 * mm)]))

        story.append(Spacer(1, 4 * mm))
        return story

    def _recommendations_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Paragraph("RECOMMENDED ACTIONS", st["section_header"]))
        story.append(_hr())

        if not r.recommendations:
            story.append(Paragraph(
                "No recommendations are available for this document.",
                st["body"]
            ))
        else:
            for rec in r.recommendations:
                prio_colour = {
                    "HIGH": C_RED, "MEDIUM": C_AMBER, "LOW": C_GREEN
                }.get(rec.priority, C_SLATE_500)

                items = [
                    Paragraph(
                        f"<b>{rec.title}</b>  [{rec.priority}]",
                        st["label"]
                    ),
                    Paragraph(rec.reason, st["body"]),
                ]
                if rec.suggested_actions:
                    for action in rec.suggested_actions:
                        items.append(Paragraph(f"• {action}", st["small"]))
                if rec.limitations:
                    items.append(Paragraph(
                        f"Limitation: {rec.limitations}", st["caption"]
                    ))
                items.append(Spacer(1, 3 * mm))
                story.append(KeepTogether(items))

        return story

    def _source_reference_block(self, r: ReportData, st: dict) -> list:
        story = []
        story.append(Spacer(1, 6 * mm))
        story.append(_hr(C_BRAND_BLUE, thickness=1.0))
        story.append(Paragraph("SOURCE DOCUMENT", st["section_header"]))
        meta = r.metadata
        data = [
            ["Document Name",  meta.document_name],
            ["Document ID",    str(meta.document_id)],
            ["Company",        meta.company_name or "Not available"],
            ["View at",        f"/documents/{meta.document_id}"],
        ]
        tbl = Table(data, colWidths=[40 * mm, CONTENT_W - 40 * mm])
        tbl.setStyle(_header_table_style())
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            f"Report ID: {meta.report_id}  ·  Generated: {meta.generated_at[:19].replace('T', ' ')} UTC",
            st["caption"]
        ))
        return story


report_pdf_renderer = ReportPDFRenderer()
