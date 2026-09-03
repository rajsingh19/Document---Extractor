"""
services/green_finance_pdf.py — Deterministic PDF Renderer for Green Finance Readiness (Step 19).

Consumes a GreenFinanceAssessmentResponse object and renders a ReportLab PDF document.
Does NOT query the database independently.
All data comes from the structured assessment payload.
"""
import io
import logging
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

from backend.app.schemas.green_finance import GreenFinanceAssessmentResponse

logger = logging.getLogger("senseible-green-finance-pdf")

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

W, H = A4
L_MARGIN = R_MARGIN = 18 * mm
T_MARGIN = B_MARGIN = 18 * mm
CONTENT_W = W - L_MARGIN - R_MARGIN


class GreenFinancePDFRenderer:
    """
    Renders deterministic ReportLab PDF for GreenFinanceAssessmentResponse.
    """

    def render(self, assessment: GreenFinanceAssessmentResponse) -> bytes:
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
        story.append(Paragraph("Green Finance Readiness Assessment Report", title_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Business: <b>{assessment.business_name}</b> | Assessment Code: <b>{assessment.assessment_code}</b> | Period: <b>{assessment.reporting_period}</b>",
            subtitle_style
        ))
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT_BLUE, spaceBefore=0, spaceAfter=4 * mm))

        # --- DISCLAIMER NOTICE ---
        disc_table = Table([[Paragraph(f"<b>CRITICAL PRODUCT DISCLAIMER:</b> {assessment.disclaimer}", disclaimer_style)]], colWidths=[CONTENT_W])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_SLATE_100),
            ("BOX", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(disc_table)
        story.append(Spacer(1, 5 * mm))

        # --- READINESS SCORE SUMMARY ---
        story.append(Paragraph("Overall Readiness Summary", h2_style))

        summary_data = [
            [
                Paragraph("<b>Readiness Score:</b>", small_style), Paragraph(f"<b>{assessment.overall_readiness_score} / 100</b>", small_style),
                Paragraph("<b>Readiness Band:</b>", small_style), Paragraph(f"<b>{assessment.readiness_band}</b>", small_style),
            ],
            [
                Paragraph("<b>Workflow Status:</b>", small_style), Paragraph(assessment.status, small_style),
                Paragraph("<b>Engine Version:</b>", small_style), Paragraph(assessment.assessment_version, small_style),
            ],
            [
                Paragraph("<b>Supported Criteria:</b>", small_style), Paragraph(f"{assessment.supported_requirements} / {assessment.total_requirements}", small_style),
                Paragraph("<b>Missing Criteria:</b>", small_style), Paragraph(f"{assessment.missing_requirements_count}", small_style),
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

        # --- 10 DIMENSIONS TABLE ---
        story.append(Paragraph("Readiness Dimensions (10 Categories)", h2_style))

        dim_rows = [
            [
                Paragraph("<b>Dimension Title</b>", small_style),
                Paragraph("<b>Score</b>", small_style),
                Paragraph("<b>Status</b>", small_style),
                Paragraph("<b>Supported Criteria</b>", small_style),
                Paragraph("<b>Explanation</b>", small_style),
            ]
        ]

        for d in assessment.dimensions:
            dim_rows.append([
                Paragraph(d.title, small_style),
                Paragraph(f"{d.score}%", small_style),
                Paragraph(d.status, small_style),
                Paragraph(f"{d.supported_count} / {d.total_count}", small_style),
                Paragraph(d.explanation, small_style),
            ])

        dim_table = Table(dim_rows, colWidths=[45 * mm, 18 * mm, 22 * mm, 25 * mm, 60 * mm])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_100]),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 6 * mm))

        # --- MISSING REQUIREMENTS & ACTIONS ---
        if assessment.missing_requirements:
            story.append(Paragraph("Missing Requirements & Action Items", h2_style))
            miss_rows = [
                [
                    Paragraph("<b>Code</b>", small_style),
                    Paragraph("<b>Requirement Name</b>", small_style),
                    Paragraph("<b>Category</b>", small_style),
                    Paragraph("<b>Priority</b>", small_style),
                    Paragraph("<b>Action Needed</b>", small_style),
                ]
            ]
            for m in assessment.missing_requirements:
                miss_rows.append([
                    Paragraph(m.requirement_code, small_style),
                    Paragraph(m.requirement_name, small_style),
                    Paragraph(m.category, small_style),
                    Paragraph(m.priority, small_style),
                    Paragraph(m.what_is_needed, small_style),
                ])
            miss_table = Table(miss_rows, colWidths=[30 * mm, 45 * mm, 30 * mm, 20 * mm, 45 * mm])
            miss_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_BRAND),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(miss_table)
            story.append(Spacer(1, 6 * mm))

        # --- METHODOLOGY NOTICE ---
        story.append(Paragraph("Methodology & Audit Disclaimer", h2_style))
        story.append(Paragraph(
            "Evaluation performed deterministically on POSTED carbon ledger accounting entries, extracted sustainability metrics, "
            "and evidence provenance. Senseible Document AI measures evidence readiness for review only and does not perform credit underwriting, "
            "loan approval decisions, or financial forecasting.",
            body_style
        ))

        doc.build(story)
        buf.seek(0)
        return buf.getvalue()


green_finance_pdf_renderer = GreenFinancePDFRenderer()
