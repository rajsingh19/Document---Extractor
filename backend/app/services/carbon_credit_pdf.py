"""
services/carbon_credit_pdf.py — Deterministic PDF Renderer for Carbon Credit Readiness & Project Eligibility Assessment (Step 20).

Consumes a CarbonCreditAssessmentResponse object and renders a comprehensive ReportLab PDF document.
All data comes deterministically from the structured assessment payload.
No LLM generation or probabilistic values.
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
    HRFlowable, KeepTogether, PageBreak
)

from backend.app.schemas.carbon_credit import CarbonCreditAssessmentResponse

logger = logging.getLogger("senseible-carbon-credit-pdf")

# Palette
C_DARK_SLATE  = HexColor("#0F172A")
C_GREEN_BRAND = HexColor("#0F6B56")
C_ACCENT_TEAL = HexColor("#0D9488")
C_SLATE_700   = HexColor("#334155")
C_SLATE_500   = HexColor("#64748B")
C_SLATE_200   = HexColor("#E2E8F0")
C_SLATE_100   = HexColor("#F1F5F9")
C_WHITE       = HexColor("#FFFFFF")
C_GREEN       = HexColor("#16A34A")
C_AMBER       = HexColor("#D97706")
C_LIGHT_GREEN = HexColor("#EAF7F2")

W, H = A4
L_MARGIN = R_MARGIN = 16 * mm
T_MARGIN = B_MARGIN = 16 * mm
CONTENT_W = W - L_MARGIN - R_MARGIN


class CarbonCreditPDFRenderer:
    """
    Renders deterministic ReportLab PDF for CarbonCreditAssessmentResponse.
    """

    def render(self, assessment: CarbonCreditAssessmentResponse) -> bytes:
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
            fontSize=18,
            leading=22,
            textColor=C_DARK_SLATE,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=C_SLATE_500,
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=C_GREEN_BRAND,
            spaceBefore=8,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=C_SLATE_700,
        )
        small_style = ParagraphStyle(
            "SmallCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=C_SLATE_700,
        )
        small_bold = ParagraphStyle(
            "SmallBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=C_DARK_SLATE,
        )
        small_header = ParagraphStyle(
            "SmallHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=C_WHITE,
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerCustom",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=C_SLATE_500,
        )

        story = []

        # 1. EXECUTIVE SUMMARY & HEADER
        story.append(Paragraph("Carbon Credit Readiness & Project Eligibility Assessment", title_style))
        story.append(Spacer(1, 1.5 * mm))
        story.append(Paragraph(
            f"Project: <b>{assessment.project_name}</b> | Assessment Code: <b>{assessment.assessment_code}</b> | Period: <b>{assessment.reporting_period}</b> | Version: <b>{assessment.assessment_version}</b>",
            subtitle_style
        ))
        story.append(Spacer(1, 3 * mm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_GREEN_BRAND, spaceBefore=0, spaceAfter=3 * mm))

        # MANDATORY DISCLAIMER
        disc_table = Table([[Paragraph(f"<b>CRITICAL PRODUCT BOUNDARY:</b> {assessment.disclaimer}", disclaimer_style)]], colWidths=[CONTENT_W])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_SLATE_100),
            ("BOX", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(disc_table)
        story.append(Spacer(1, 4 * mm))

        # 2. PROJECT INFORMATION & 3. READINESS SCORE
        story.append(Paragraph("1. Project Information & Readiness Score", h2_style))

        proj_info_data = [
            [
                Paragraph("<b>Project Name:</b>", small_bold), Paragraph(assessment.project_name, small_style),
                Paragraph("<b>Readiness Score:</b>", small_bold), Paragraph(f"<b>{assessment.overall_readiness_score:.2f} / 100</b>", small_bold),
            ],
            [
                Paragraph("<b>Project Category:</b>", small_bold), Paragraph(assessment.project_category or "Unspecified", small_style),
                Paragraph("<b>Readiness Band:</b>", small_bold), Paragraph(assessment.readiness_band, small_bold),
            ],
            [
                Paragraph("<b>Project Scope:</b>", small_bold), Paragraph(assessment.project_scope or "N/A", small_style),
                Paragraph("<b>Assessment Status:</b>", small_bold), Paragraph(assessment.status, small_style),
            ],
            [
                Paragraph("<b>Project Owner:</b>", small_bold), Paragraph(assessment.project_owner or "Unassigned", small_style),
                Paragraph("<b>Methodology Status:</b>", small_bold), Paragraph(assessment.methodology_status, small_style),
            ],
            [
                Paragraph("<b>Baseline Reference:</b>", small_bold), Paragraph(f"{assessment.baseline_period or 'None'} ({assessment.baseline_co2e or 0} {assessment.baseline_co2e_unit or 'kgCO2e'})", small_style),
                Paragraph("<b>Standard Alignment:</b>", small_bold), Paragraph(assessment.standard_status, small_style),
            ],
        ]
        info_table = Table(proj_info_data, colWidths=[35 * mm, 50 * mm, 38 * mm, 47 * mm])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 4 * mm))

        # 4. READINESS DIMENSIONS (15 Categories)
        story.append(Paragraph("2. Readiness Dimensions Assessment", h2_style))

        dim_rows = [
            [
                Paragraph("<b>Dimension Title</b>", small_header),
                Paragraph("<b>Score</b>", small_header),
                Paragraph("<b>Status</b>", small_header),
                Paragraph("<b>Supported</b>", small_header),
                Paragraph("<b>Evaluation Summary</b>", small_header),
            ]
        ]
        for d in assessment.dimensions:
            dim_rows.append([
                Paragraph(d.title, small_bold),
                Paragraph(f"{d.score:.1f}%", small_style),
                Paragraph(d.status, small_style),
                Paragraph(f"{d.supported_count}/{d.total_count}", small_style),
                Paragraph(d.explanation, small_style),
            ])

        dim_table = Table(dim_rows, colWidths=[42 * mm, 16 * mm, 22 * mm, 20 * mm, 70 * mm])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_GREEN_BRAND),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_100]),
            ("PADDING", (0, 0), (-1, -1), 3.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 4 * mm))

        # 5. CARBON ACCOUNTING & 6. BASELINE READINESS
        story.append(Paragraph("3. Carbon Accounting & Baseline Verification", h2_style))
        acct = assessment.accounting_summary
        acct_rows = [
            [
                Paragraph("<b>Accounted Emissions:</b>", small_bold),
                Paragraph(f"{acct.accounted_emissions_tco2e:.4f} tCO2e" if acct and acct.accounted_emissions_tco2e is not None else "Not Recorded", small_style),
                Paragraph("<b>Posted Ledger Entries:</b>", small_bold),
                Paragraph(str(acct.posted_ledger_entries_count if acct else 0), small_style),
            ],
            [
                Paragraph("<b>Baseline CO2e Reference:</b>", small_bold),
                Paragraph(f"{acct.baseline_co2e_tco2e:.4f} tCO2e" if acct and acct.baseline_co2e_tco2e is not None else "Not Set", small_style),
                Paragraph("<b>Observed Reduction:</b>", small_bold),
                Paragraph(f"{acct.observed_reduction_tco2e:.4f} tCO2e" if acct and acct.observed_reduction_tco2e is not None else "Pending Measurement", small_style),
            ],
        ]
        acct_table = Table(acct_rows, colWidths=[40 * mm, 45 * mm, 40 * mm, 45 * mm])
        acct_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(acct_table)
        story.append(Paragraph("<font size=7 color='#64748B'>* Note: All figures represent accounted/measured CO2e emissions derived from POSTED CarbonLedgerEntry records. They do NOT represent carbon credits.</font>", small_style))
        story.append(Spacer(1, 4 * mm))

        # 7. REDUCTION EVIDENCE, 8. ADDITIONALITY, 9. MONITORING, 10. MEASUREMENT, 11. VERIFICATION
        story.append(Paragraph("4. Project Development & Verification Posture", h2_style))
        meth = assessment.methodology
        dev_rows = [
            [
                Paragraph("<b>Methodology Review Status:</b>", small_bold), Paragraph(meth.overall_methodology_status if meth else "NEEDS_REVIEW", small_style),
                Paragraph("<b>Carbon Standard Framework:</b>", small_bold), Paragraph(meth.framework if meth else "GENERIC_CARBON_STANDARD", small_style),
            ],
            [
                Paragraph("<b>Baseline Status:</b>", small_bold), Paragraph(meth.baseline_status if meth else "NEEDS_REVIEW", small_style),
                Paragraph("<b>Monitoring Plan Status:</b>", small_bold), Paragraph(meth.monitoring_status if meth else "NEEDS_REVIEW", small_style),
            ],
            [
                Paragraph("<b>Emissions Traceability:</b>", small_bold), Paragraph(meth.emissions_traceability_status if meth else "NEEDS_REVIEW", small_style),
                Paragraph("<b>Independent Verification:</b>", small_bold), Paragraph(meth.verification_pathway_status if meth else "NOT_RECORDED", small_style),
            ],
        ]
        dev_table = Table(dev_rows, colWidths=[45 * mm, 40 * mm, 45 * mm, 40 * mm])
        dev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(dev_table)
        story.append(Spacer(1, 4 * mm))

        # 12. METHODOLOGY & 13. STANDARD READINESS DISCLAIMER
        story.append(Paragraph(
            "<b>Additionality & Standard Boundary:</b> Senseible does not determine additionality or certify compliance with specific registries "
            "(e.g. Verra VCS, Gold Standard). Additionality requires independent methodology evaluation. Baseline information available is for methodology review.",
            disclaimer_style
        ))
        story.append(Spacer(1, 4 * mm))

        # 14. EVIDENCE SOURCES
        if assessment.requirements:
            evidence_found = []
            for r in assessment.requirements:
                for ev in r.evidence_items:
                    evidence_found.append((r.requirement_name, ev.source_type or "N/A", ev.source_field or "N/A", ev.source_text or ""))

            if evidence_found:
                story.append(Paragraph("5. Evidence Lineage & Provenance", h2_style))
                ev_rows = [
                    [
                        Paragraph("<b>Requirement</b>", small_header),
                        Paragraph("<b>Source Type</b>", small_header),
                        Paragraph("<b>Source Field</b>", small_header),
                        Paragraph("<b>Evidence Detail</b>", small_header),
                    ]
                ]
                for req_n, st, sf, stxt in evidence_found[:6]:
                    ev_rows.append([
                        Paragraph(req_n, small_style),
                        Paragraph(st, small_style),
                        Paragraph(sf, small_style),
                        Paragraph(stxt[:80] + ("..." if len(stxt) > 80 else ""), small_style),
                    ])
                ev_table = Table(ev_rows, colWidths=[45 * mm, 30 * mm, 30 * mm, 65 * mm])
                ev_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), C_GREEN_BRAND),
                    ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
                    ("PADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(ev_table)
                story.append(Spacer(1, 4 * mm))

        # 15. MISSING REQUIREMENTS & 16. NEXT ACTIONS
        if assessment.missing_requirements:
            story.append(Paragraph("6. Missing Requirements & Recommended Actions", h2_style))
            miss_rows = [
                [
                    Paragraph("<b>Code</b>", small_header),
                    Paragraph("<b>Requirement</b>", small_header),
                    Paragraph("<b>Priority</b>", small_header),
                    Paragraph("<b>Recommended Next Action</b>", small_header),
                ]
            ]
            for m in assessment.missing_requirements[:8]:
                miss_rows.append([
                    Paragraph(m.requirement_code, small_bold),
                    Paragraph(m.requirement_name, small_style),
                    Paragraph(m.priority, small_style),
                    Paragraph(m.recommended_action, small_style),
                ])
            miss_table = Table(miss_rows, colWidths=[25 * mm, 45 * mm, 20 * mm, 80 * mm])
            miss_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_GREEN_BRAND),
                ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_100]),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(miss_table)
            story.append(Spacer(1, 4 * mm))

        # 17. CERTIFICATION PATHWAY CHECKLIST
        if assessment.checklist:
            story.append(Paragraph("7. Project Certification Pathway Checklist", h2_style))
            chk_rows = [
                [
                    Paragraph("<b>#</b>", small_header),
                    Paragraph("<b>Section</b>", small_header),
                    Paragraph("<b>Status</b>", small_header),
                    Paragraph("<b>Requirements Included</b>", small_header),
                ]
            ]
            for chk in assessment.checklist:
                chk_rows.append([
                    Paragraph(str(chk.section_number), small_bold),
                    Paragraph(chk.section_name, small_bold),
                    Paragraph(chk.status, small_style),
                    Paragraph(chk.description[:90] + ("..." if len(chk.description) > 90 else ""), small_style),
                ])
            chk_table = Table(chk_rows, colWidths=[10 * mm, 38 * mm, 22 * mm, 100 * mm])
            chk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), C_GREEN_BRAND),
                ("GRID", (0, 0), (-1, -1), 0.5, C_SLATE_200),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_100]),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(chk_table)
            story.append(Spacer(1, 4 * mm))

        # 18. METHODOLOGY / SCORING & 19. MANDATORY DISCLAIMER
        story.append(Paragraph("8. Deterministic Scoring Methodology & Final Notice", h2_style))
        story.append(Paragraph(
            "<b>Scoring Formula:</b> Score = SUM(weight * completion) / SUM(applicable weights) * 100. "
            "Completion Multipliers: SUPPORTED = 1.00, PARTIALLY_SUPPORTED = 0.50, NEEDS_REVIEW = 0.25, MISSING = 0.00. "
            "Bands: 0–39 (NOT_READY), 40–69 (PARTIALLY_READY), 70–100 (READY_FOR_METHODOLOGY_REVIEW).<br/><br/>"
            "<b>Final Notice:</b> Senseible Document AI assesses project readiness to begin methodology and standard review. "
            "It does NOT issue carbon credits, estimate credit quantity, guarantee revenue, predict market price, or certify additionality. "
            "External validation/verification by an accredited validation/verification body (VVB) is required for formal registry registration.",
            body_style
        ))

        doc.build(story)
        buf.seek(0)
        return buf.getvalue()


carbon_credit_pdf_renderer = CarbonCreditPDFRenderer()
