"""
services/compliance_report_pdf.py — Deterministic PDF Renderer for Compliance Reports (Step 18).

Consumes a ComplianceReportResponse object and renders a ReportLab PDF document.
Does NOT query the database independently.
All data comes from the structured report payload.
"""
import io
import logging
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)

from backend.app.schemas.compliance_report import ComplianceReportResponse

logger = logging.getLogger("senseible-compliance-pdf")

# Palette
C_DARK_SLATE  = HexColor("#0F172A")
C_BLUE_BRAND  = HexColor("#1E3A5F")
C_ACCENT_BLUE = HexColor("#2563EB")
C_SLATE_700   = HexColor("#334155")
C_SLATE_500   = HexColor("#64748B")
C_SLATE_200   = HexColor("#E2E8F0")
C_SLATE_100   = HexColor("#F1F5F9")
C_WHITE       = HexColor("#FFFFFF")
C_GREEN       = HexColor("#16A34A")
C_AMBER       = HexColor("#D97706")
C_RED         = HexColor("#DC2626")
C_PURPLE      = HexColor("#7C3AED")

W, H = A4
L_MARGIN = R_MARGIN = 18 * mm
T_MARGIN = B_MARGIN = 18 * mm
CONTENT_W = W - L_MARGIN - R_MARGIN


class ComplianceReportPDFRenderer:
    """
    Renders deterministic ReportLab PDF for a ComplianceReportResponse.
    """

    def render(self, report: ComplianceReportResponse) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=L_MARGIN,
            rightMargin=R_MARGIN,
            topMargin=T_MARGIN,
            bottomMargin=B_MARGIN,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=C_DARK_SLATE,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=C_SLATE_500,
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=C_BLUE_BRAND,
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=C_SLATE_700,
        )
        small_style = ParagraphStyle(
            "SmallCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=C_SLATE_500,
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerCustom",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=C_SLATE_500,
        )

        story = []

        # --- HEADER SECTION ---
        story.append(Paragraph(report.report_name, title_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"Framework: <b>{report.framework} v{report.framework_version}</b> | Reporting Period: <b>{report.reporting_period}</b>", subtitle_style))
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT_BLUE, spaceBefore=0, spaceAfter=4 * mm))

        # --- DISCLAIMER NOTICE ---
        disclaimer_box = [
            [Paragraph(f"<b>REPORT PREPARATION NOTICE:</b> {report.disclaimer}", disclaimer_style)]
        ]
        disc_table = Table(disclaimer_box, colWidths=[CONTENT_W])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_SLATE_100),
            ("BOX", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(disc_table)
        story.append(Spacer(1, 5 * mm))

        # --- REPORT SUMMARY METRICS ---
        story.append(Paragraph("Report Summary & Completeness Overview", h2_style))

        summary_data = [
            [
                Paragraph("<b>Report Code:</b>", small_style), Paragraph(report.report_code, small_style),
                Paragraph("<b>Organization:</b>", small_style), Paragraph(report.organization_name, small_style),
            ],
            [
                Paragraph("<b>Workflow Status:</b>", small_style), Paragraph(f"<b>{report.status}</b>", small_style),
                Paragraph("<b>Completeness:</b>", small_style), Paragraph(f"<b>{report.completeness_status}</b>", small_style),
            ],
            [
                Paragraph("<b>Assurance Status:</b>", small_style), Paragraph(report.assurance_status, small_style),
                Paragraph("<b>Data Quality:</b>", small_style), Paragraph(report.data_quality_status, small_style),
            ],
            [
                Paragraph("<b>Supported Disclosures:</b>", small_style), Paragraph(f"{report.supported_disclosures} / {report.total_disclosures}", small_style),
                Paragraph("<b>Missing Disclosures:</b>", small_style), Paragraph(f"{report.missing_disclosures}", small_style),
            ],
        ]
        sum_table = Table(summary_data, colWidths=[35 * mm, 50 * mm, 35 * mm, 50 * mm])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 6 * mm))

        # --- SECTIONS & DISCLOSURES ---
        for sec in report.sections:
            story.append(Paragraph(f"{sec.section_title} (Completeness: {sec.completeness})", h2_style))

            table_rows = [
                [
                    Paragraph("<b>Disclosure Code</b>", small_style),
                    Paragraph("<b>Title</b>", small_style),
                    Paragraph("<b>Reported Value</b>", small_style),
                    Paragraph("<b>Status</b>", small_style),
                    Paragraph("<b>Source</b>", small_style),
                ]
            ]

            for d in sec.disclosures:
                val_display = f"{d.value} {d.value_unit or ''}".strip() if d.value else "MISSING / UNAVAILABLE"
                status_color = "green" if d.status == "SUPPORTED" else ("orange" if d.status == "NEEDS_REVIEW" else "red")
                status_p = Paragraph(f"<font color='{status_color}'><b>{d.status}</b></font>", small_style)

                table_rows.append([
                    Paragraph(d.disclosure_code, small_style),
                    Paragraph(d.disclosure_title, small_style),
                    Paragraph(val_display, small_style),
                    status_p,
                    Paragraph(d.source_type, small_style),
                ])

            sec_table = Table(table_rows, colWidths=[32 * mm, 55 * mm, 38 * mm, 25 * mm, 20 * mm])
            sec_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_BRAND),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_100]),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(sec_table)
            story.append(Spacer(1, 5 * mm))

        # --- METHODOLOGY & LIMITATIONS NOTICE ---
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Methodology & Audit Disclaimer", h2_style))
        story.append(Paragraph(
            "Prepared from available document evidence, normalized activity data, and POSTED carbon ledger accounting entries. "
            "Senseible Document AI does not perform independent third-party audit or regulatory certification. "
            "External assurance requires review by an accredited independent verifier.",
            body_style
        ))

        doc.build(story)
        buf.seek(0)
        return buf.getvalue()


compliance_pdf_renderer = ComplianceReportPDFRenderer()
