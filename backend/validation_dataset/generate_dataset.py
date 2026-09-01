import os
import math
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = [
    "01_electricity_bills",
    "02_fuel_receipts",
    "03_water_bills",
    "04_commercial_invoices",
    "05_waste_manifests",
    "06_esg_reports",
    "07_scanned_documents",
    "08_edge_cases"
]

for d in DIRS:
    os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

# -------------------------------------------------------------
# 01 ELECTRICITY BILLS
# -------------------------------------------------------------
def gen_01_clean_electricity():
    path = os.path.join(BASE_DIR, "01_electricity_bills", "01_clean_electricity_bill.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#0F172A'), alignment=1)
    sub_style = ParagraphStyle('S1', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#475569'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))
    head_style = ParagraphStyle('H1', parent=styles['Heading2'], fontSize=10, leading=13, textColor=colors.HexColor('#0F172A'), spaceBefore=6, spaceAfter=3)

    story = [
        Paragraph("GUJARAT STATE ELECTRICITY TRANSMISSION CORP", title_style),
        Paragraph("Industrial High-Tension (HT-1) Tariff Power Bill", sub_style),
        Spacer(1, 10),
    ]

    header_data = [
        [Paragraph("<b>Consumer Name:</b> Shree Balaji Components Pvt. Ltd.", body_style), Paragraph("<b>Bill Number:</b> GUVNL-HT-2024-88412", body_style)],
        [Paragraph("<b>Location:</b> Phase 2, Vatva Industrial Estate, Ahmedabad, Gujarat", body_style), Paragraph("<b>Billing Month:</b> October 2024", body_style)],
        [Paragraph("<b>Contract Demand:</b> 250.00 kVA", body_style), Paragraph("<b>Billing Period:</b> 2024-10-01 to 2024-10-31", body_style)],
        [Paragraph("<b>GSTIN:</b> 24AAACB1122D1Z4", body_style), Paragraph("<b>Tariff Category:</b> HTP-I Industrial", body_style)]
    ]
    t_head = Table(header_data, colWidths=[270, 270])
    t_head.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_head)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Metered Energy & Demand Data</b>", head_style))
    m_data = [
        ["Parameter", "Recorded Metric", "Unit", "Billing Basis"],
        ["Total Active Electricity Consumption", "82,450.00", "kWh", "Metered Units"],
        ["Recorded Peak Demand", "215.50", "kVA", "Peak Billed Demand"],
        ["Average Power Factor", "0.97", "PF", "Bonus Eligible (>0.95)"],
        ["Reactive Energy", "12,100.00", "kVArh", "Normal"]
    ]
    t_m = Table(m_data, colWidths=[210, 110, 80, 140])
    t_m.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Financial Charges & Taxes</b>", head_style))
    c_data = [
        ["Line Item Description", "Computation Basis", "Amount (INR)"],
        ["Energy Charges", "82,450 kWh @ Rs. 6.20/kWh", "511,190.00"],
        ["Demand Fixed Charges", "215.50 kVA @ Rs. 320/kVA", "68,960.00"],
        ["Fuel Surcharge (FPPPA)", "82,450 kWh @ Rs. 0.42/kWh", "34,629.00"],
        ["Power Factor Rebate Incentive", "0.97 PF Bonus (-1.5%)", "-8,700.00"],
        ["Electricity Duty (15%) & Cess", "State Statutory Duty", "42,196.50"],
        ["Total Amount Payable", "Net Payable Invoice Total", "INR 648,275.50"]
    ]
    t_c = Table(c_data, colWidths=[220, 180, 140])
    t_c.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_c)
    doc.build(story)

def gen_02_indian_format_electricity():
    path = os.path.join(BASE_DIR, "01_electricity_bills", "02_indian_format_electricity_bill.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))
    head_style = ParagraphStyle('H1', parent=styles['Heading2'], fontSize=10, leading=13, textColor=colors.HexColor('#0F172A'), spaceBefore=6, spaceAfter=3)

    story = [
        Paragraph("DAKSHIN GUJARAT VIJ COMPANY LIMITED (DGVCL)", title_style),
        Paragraph("Industrial MSME Textile Power Consumption Statement - Billing Period: October 2024", body_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Omkar Textile Processing MSME", body_style), Paragraph("<b>Consumer No:</b> 04/991/4412/10", body_style)],
        [Paragraph("<b>Address:</b> GIDC Pandesara, Surat, Gujarat 394221", body_style), Paragraph("<b>Bill Month:</b> October 2024", body_style)],
        [Paragraph("<b>GSTIN:</b> 24AAAFO9988A1Z7", body_style), Paragraph("<b>Contract Demand:</b> 2,500.00 kVA", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Energy Consumption Profile (Indian Number Formatting)</b>", head_style))
    m_data = [
        ["Energy Source / Metric", "Recorded Volume", "Unit", "Tariff Rate"],
        ["Grid Electricity Consumption", "1,25,500.00", "kWh", "Rs. 7.45 per kWh"],
        ["Captive Rooftop Solar Generation", "15,000.00", "kWh", "Solar Net-Metered"],
        ["Recorded Peak Demand Load", "2,450.00", "kVA", "Rs. 350.00 per kVA"],
        ["Diesel Generator Backup Fuel", "800.00", "Liters", "Generator HSD Fuel"],
        ["Power Factor Average", "0.96", "PF", "Compliant"]
    ]
    t_m = Table(m_data, colWidths=[200, 110, 80, 150])
    t_m.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065F46')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0FDF4')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Invoice Breakdown & GST Calculations</b>", head_style))
    c_data = [
        ["Description", "Amount in INR (Indian Lakhs Format)"],
        ["Total Energy Charges (1,25,500 kWh)", "Rs. 9,34,975.00"],
        ["Demand Load Charges (2,450 kVA)", "Rs. 1,85,000.00"],
        ["Fuel Surcharge & Cess", "Rs. 45,805.50"],
        ["GST (CGST 9% + SGST 9%)", "Rs. 80,000.00"],
        ["Total Net Payable Amount", "INR 12,45,780.50"]
    ]
    t_c = Table(c_data, colWidths=[300, 240])
    t_c.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_c)
    doc.build(story)

def gen_03_missing_fields_electricity():
    path = os.path.join(BASE_DIR, "01_electricity_bills", "03_missing_fields_electricity_bill.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("UTILITY ELECTRICITY SUPPLY VOUCHER", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Pragati Machine Tools", body_style), Paragraph("<b>Bill Number:</b> ELEC-PMT-2024-11", body_style)],
        [Paragraph("<b>Location:</b> Industrial Area, Rajkot, Gujarat", body_style), Paragraph("<b>Billing Period:</b> November 2024", body_style)],
        [Paragraph("<b>Customer Ref:</b> CUST-77441", body_style), Paragraph("<b>Issue Date:</b> 2024-11-28", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    m_data = [
        ["Line Item Description", "Quantity", "Unit", "Total (INR)"],
        ["Active Grid Electricity Consumed", "45,200.00", "kWh", "316,400.00"],
        ["Municipal Utility Tax", "-", "-", "25,312.00"],
        ["Total Amount Payable", "-", "-", "INR 341,712.00"]
    ]
    t_m = Table(m_data, colWidths=[220, 100, 80, 140])
    t_m.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Note: Sub-metering for peak demand kVA, power factor log, and diesel generator logs are not maintained on this bill.</i>", body_style))
    doc.build(story)

# -------------------------------------------------------------
# 02 FUEL RECEIPTS
# -------------------------------------------------------------
def gen_04_clean_fuel():
    path = os.path.join(BASE_DIR, "02_fuel_receipts", "04_clean_fuel_receipt.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#7C2D12'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("NATIONAL PETRO SERVICES & BULK FUEL DISPATCH", title_style),
        Paragraph("Commercial Diesel Fuel Supply Delivery Receipt", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Customer Name:</b> Kaveri Auto Parts", body_style), Paragraph("<b>Receipt No:</b> PETRO-REC-2024-5541", body_style)],
        [Paragraph("<b>Dispatch Station:</b> NH-48 Fuel Terminal, Vadodara", body_style), Paragraph("<b>Delivery Date:</b> 2024-10-12", body_style)],
        [Paragraph("<b>GSTIN:</b> 24AABCK5512L1Z9", body_style), Paragraph("<b>Vehicle No:</b> GJ-06-AX-4412", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FDE68A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FEF3C7')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    f_data = [
        ["Fuel Description", "Quantity", "Unit Rate (INR)", "Tax Amount", "Total Payable (INR)"],
        ["High Speed Diesel (HSD) - Commercial", "850.50 Liters", "91.25 / L", "11,845.22", "INR 77,608.13"]
    ]
    t_f = Table(f_data, colWidths=[180, 90, 80, 80, 110])
    t_f.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#B45309')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_f)
    doc.build(story)

def gen_05_confusing_numbers_fuel():
    path = os.path.join(BASE_DIR, "02_fuel_receipts", "05_confusing_numbers_fuel_receipt.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("SHIVAM HIGHWAY PETROLEUM LOGISTICS", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Kaveri Auto Parts", body_style), Paragraph("<b>Invoice No:</b> INV-998877", body_style)],
        [Paragraph("<b>HSN Code:</b> 27101930 (Mineral Diesel)", body_style), Paragraph("<b>Date:</b> 2024-10-25", body_style)],
        [Paragraph("<b>GSTIN:</b> 24AAACS7711B1Z2", body_style), Paragraph("<b>Purchase Order:</b> PO-554433", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    f_data = [
        ["Item Description", "HSN Code", "Volume Dispatched", "GST Tax (INR)", "Total Invoice Amount"],
        ["Diesel Generator Industrial Fuel", "HSN: 27101930", "1,200 Liters", "Rs. 18,450.00", "INR 127,500.00"]
    ]
    t_f = Table(f_data, colWidths=[170, 80, 90, 90, 110])
    t_f.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_f)
    doc.build(story)

# -------------------------------------------------------------
# 03 WATER BILLS
# -------------------------------------------------------------
def gen_06_industrial_water():
    path = os.path.join(BASE_DIR, "03_water_bills", "06_industrial_water_bill.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#0369A1'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("UTTAR PRADESH JAL SANSTHAN INDUSTRIAL WATER SUPPLY", title_style),
        Paragraph("Monthly Industrial Water & Effluent Billing Statement", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Consumer Name:</b> Ganga Foods Processing Unit", body_style), Paragraph("<b>Connection No:</b> WTR-LKO-2024-9981", body_style)],
        [Paragraph("<b>Location:</b> UPSIDC Industrial Area, Kursi Road, Lucknow, UP", body_style), Paragraph("<b>Billing Month:</b> October 2024", body_style)],
        [Paragraph("<b>Meter Serial:</b> WM-882241", body_style), Paragraph("<b>Billing Period:</b> 2024-10-01 to 2024-10-31", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BAE6FD')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0F2FE')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    w_data = [
        ["Water Flow Category", "Metered Volume", "Unit", "Rate / kL", "Charge (INR)"],
        ["Freshwater Municipal Intake", "8,450.00", "kL", "15.00 / kL", "126,750.00"],
        ["Treated / Recycled Industrial Water", "2,100.00", "kL", "6.00 / kL", "12,600.00"],
        ["Industrial Sewage & Drainage Surcharge", "-", "-", "-", "5,850.00"],
        ["Total Water Supply Charges", "-", "-", "-", "INR 145,200.00"]
    ]
    t_w = Table(w_data, colWidths=[180, 90, 60, 90, 120])
    t_w.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0F9FF')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_w)
    doc.build(story)

def gen_07_missing_recycled_water():
    path = os.path.join(BASE_DIR, "03_water_bills", "07_missing_recycled_water_bill.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#0369A1'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("MUNICIPAL WATER SUPPLY BILL", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Customer Name:</b> Yamuna Beverages MSME", body_style), Paragraph("<b>Bill No:</b> WTR-YB-2024-11", body_style)],
        [Paragraph("<b>Billing Month:</b> November 2024", body_style), Paragraph("<b>Issue Date:</b> 2024-11-25", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BAE6FD')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0F2FE')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    w_data = [
        ["Description", "Volume", "Unit", "Total Charge (INR)"],
        ["Freshwater Industrial Consumption", "6,750.00", "kL", "101,250.00"],
        ["Sanitation Service Charge", "-", "-", "8,200.00"],
        ["Net Amount Payable", "-", "-", "INR 109,450.00"]
    ]
    t_w = Table(w_data, colWidths=[220, 100, 80, 140])
    t_w.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_w)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Note: Facility does not operate an on-site recycling unit; recycled water flow is null.</i>", body_style))
    doc.build(story)

# -------------------------------------------------------------
# 04 COMMERCIAL INVOICES
# -------------------------------------------------------------
def gen_08_material_invoice():
    path = os.path.join(BASE_DIR, "04_commercial_invoices", "08_material_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("SHAKTI INDUSTRIAL SUPPLIES", title_style),
        Paragraph("Tax Invoice / Commercial Bill of Supply", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Buyer / Consignee:</b> Rajasthan Precision Metals", body_style), Paragraph("<b>Invoice No:</b> SIS-2024-8841", body_style)],
        [Paragraph("<b>Buyer GSTIN:</b> 08AAACR8844K1Z3", body_style), Paragraph("<b>Invoice Date:</b> 2024-10-18", body_style)],
        [Paragraph("<b>Seller GSTIN:</b> 08AAACS1144J1Z8", body_style), Paragraph("<b>Payment Terms:</b> 30 Days Net", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    item_data = [
        ["Item Description", "Quantity", "Unit", "Unit Rate (INR)", "Amount (INR)"],
        ["Steel Sheets (Cold Rolled)", "250.00", "kg", "145.00", "36,250.00"],
        ["Aluminium Rods 6061", "120.00", "kg", "280.00", "33,600.00"],
        ["Copper Wire Grade A", "75.00", "kg", "620.00", "46,500.00"],
        ["Subtotal Before Tax", "-", "-", "-", "116,350.00"],
        ["CGST (9%) + SGST (9%)", "-", "-", "-", "20,943.00"],
        ["Total Invoice Value", "-", "-", "-", "INR 137,293.00"]
    ]
    t_item = Table(item_data, colWidths=[180, 70, 60, 100, 130])
    t_item.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-3), [colors.white, colors.HexColor('#F8FAFC')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_item)
    doc.build(story)

def gen_09_indian_format_invoice():
    path = os.path.join(BASE_DIR, "04_commercial_invoices", "09_indian_format_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("MAHALAXMI HEAVY ENGINEERING TAX INVOICE", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Billed To:</b> Mahalaxmi Heavy Engineering", body_style), Paragraph("<b>Invoice No:</b> MHE-2024-9912", body_style)],
        [Paragraph("<b>GSTIN:</b> 27AABCM7722K1ZX", body_style), Paragraph("<b>Date:</b> 2024-10-22", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    item_data = [
        ["Item Description", "Qty", "Amount (INR with Indian Format)"],
        ["Heavy CNC Lathe Tooling Kit", "1 Set", "Rs. 1,25,000.00"],
        ["Industrial Gearbox Assembly 50HP", "2 Units", "Rs. 2,48,750.00"],
        ["Hydraulic Directional Control Valves", "5 Units", "Rs. 18,450.00"],
        ["GST Tax Amount @ 18%", "-", "Rs. 1,00,000.00"],
        ["Total Payable Invoice Amount", "-", "INR 4,92,200.00"]
    ]
    t_item = Table(item_data, colWidths=[270, 70, 200])
    t_item.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_item)
    doc.build(story)

def gen_10_sustainability_materials_invoice():
    path = os.path.join(BASE_DIR, "04_commercial_invoices", "10_sustainability_materials_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("GREEN MATRIX INDUSTRIAL SUPPLIES", title_style),
        Paragraph("Commercial Tax Invoice - Dispatch Manifest", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Customer:</b> EcoPack Manufacturing MSME", body_style), Paragraph("<b>Invoice No:</b> GMS-2024-4412", body_style)],
        [Paragraph("<b>Address:</b> Phase 1, GIDC Naroda, Ahmedabad", body_style), Paragraph("<b>Date:</b> 2024-10-20", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    item_data = [
        ["Line Item / Material Description", "Quantity", "Unit", "Total Charge (INR)"],
        ["Recycled Steel Strapping Bands", "500.00", "kg", "45,000.00"],
        ["Virgin Steel Binding Wire", "200.00", "kg", "22,000.00"],
        ["Kraft Packaging Paper Roll", "150.00", "kg", "12,000.00"],
        ["Polyethylene Plastic Stretch Film", "80.00", "kg", "9,600.00"],
        ["Total Commercial Invoice Value", "-", "-", "INR 88,600.00"]
    ]
    t_item = Table(item_data, colWidths=[220, 80, 80, 160])
    t_item.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_item)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Note: Standard commercial purchase order. Not an environmental audit report.</i>", body_style))
    doc.build(story)

# -------------------------------------------------------------
# 05 WASTE MANIFESTS
# -------------------------------------------------------------
def gen_11_clean_waste_manifest():
    path = os.path.join(BASE_DIR, "05_waste_manifests", "11_clean_waste_manifest.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#92400E'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("HAZARDOUS & INDUSTRIAL WASTE MANIFEST (FORM 10)", title_style),
        Paragraph("Hazardous and Other Wastes (Management & Transboundary Movement) Rules 2016", ParagraphStyle('S', parent=styles['Normal'], fontSize=8.5, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Sender / Generator:</b> Narmada Chemical Products", body_style), Paragraph("<b>Manifest No:</b> WM-2024-8812", body_style)],
        [Paragraph("<b>Facility Location:</b> GIDC Ankleshwar, Gujarat", body_style), Paragraph("<b>Dispatch Date:</b> 2024-10-14", body_style)],
        [Paragraph("<b>Transporter:</b> SafeLogistics Hazardous Transport", body_style), Paragraph("<b>Vehicle No:</b> GJ-16-Z-9941", body_style)],
        [Paragraph("<b>TSDF Destination:</b> Gujarat Enviro TSDF Facility", body_style), Paragraph("<b>PCB Consent:</b> PCB/HAZ/ANK/2024/77", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FDE68A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FEF3C7')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    w_data = [
        ["Waste Category / Schedule", "Description", "Dispatched Qty", "Unit", "Disposal Route"],
        ["Schedule 1 - Cat 35.3", "Chemical Sludge / Hazardous Waste", "3,250.00", "kg", "Secured Landfill (TSDF)"],
        ["Schedule 1 - Cat 5.1", "Used Lubricant Oil", "740.00", "Liters", "Authorized Re-refiner"],
        ["Non-Hazardous Industrial", "Polymer Process Waste", "460.00", "kg", "Secondary Co-processing"]
    ]
    t_w = Table(w_data, colWidths=[120, 160, 80, 60, 120])
    t_w.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#B45309')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FFFBEB')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_w)
    doc.build(story)

def gen_12_missing_quantities_waste():
    path = os.path.join(BASE_DIR, "05_waste_manifests", "12_missing_quantities_waste_manifest.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#92400E'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("WASTE DISPATCH LOG - LOGISTICS DOCKET", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Godavari Industrial Chemicals", body_style), Paragraph("<b>Manifest No:</b> WM-2024-9901", body_style)],
        [Paragraph("<b>Transporter:</b> CleanTrans Industrial Logistics", body_style), Paragraph("<b>Dispatch Date:</b> 2024-11-05", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FDE68A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FEF3C7')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    w_data = [
        ["Waste Type", "Physical State", "Recorded Quantity", "Unit"],
        ["ETP Chemical Sludge", "Solid Filter Cake", "1,850.00", "kg"],
        ["Spent Process Solvent", "Liquid", "— (Pending Lab Weighbridge)", "—"],
        ["Contaminated Container Scrap", "Solid Metal Drums", "420.00", "kg"]
    ]
    t_w = Table(w_data, colWidths=[180, 120, 140, 100])
    t_w.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#B45309')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_w)
    doc.build(story)

# -------------------------------------------------------------
# 06 ESG REPORTS (Multi-Page)
# -------------------------------------------------------------
def gen_13_multipage_esg():
    path = os.path.join(BASE_DIR, "06_esg_reports", "13_multipage_esg_report.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#065F46'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))
    head_style = ParagraphStyle('H1', parent=styles['Heading2'], fontSize=11, leading=14, textColor=colors.HexColor('#065F46'), spaceBefore=8, spaceAfter=4)

    story = [
        # PAGE 1: Corporate Profile
        Paragraph("HIMALAYAN MANUFACTURING INDUSTRIES", title_style),
        Paragraph("Annual ESG & Environmental Sustainability Audit Report - FY2023-24", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 14),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Himalayan Manufacturing Industries", body_style), Paragraph("<b>Audit Ref:</b> ESG-HMI-2023-24", body_style)],
        [Paragraph("<b>Business Sector:</b> Heavy Engineering & Precision Auto Components", body_style), Paragraph("<b>Reporting Period:</b> 2023-04-01 to 2024-03-31", body_style)],
        [Paragraph("<b>Facility Location:</b> Industrial Cluster, Haridwar, Uttarakhand", body_style), Paragraph("<b>Certifications:</b> ISO 14001:2015, ISO 9001:2015", body_style)],
        [Paragraph("<b>Auditor Agency:</b> EcoAudit Global Standards Ltd.", body_style), Paragraph("<b>Compliance Status:</b> Compliant", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ECFDF5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#A7F3D0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1FAE5')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 14))
    story.append(Paragraph("<b>Executive Summary:</b> This annual sustainability disclosure presents comprehensive environmental indicators across energy utilization, water consumption, circular waste management, and Scope 1 and Scope 2 greenhouse gas emissions for the audited financial year.", body_style))
    story.append(PageBreak())

    # PAGE 2: Resource & Waste Data
    story.append(Paragraph("<b>Section 1: Energy, Water & Waste Resource Profile</b>", head_style))
    story.append(Spacer(1, 8))
    
    r_data = [
        ["Resource Parameter", "Annual Volume", "Unit", "Performance Note"],
        ["Total Electricity Consumption", "340,000.00", "kWh", "Grid Power"],
        ["Freshwater Municipal Withdrawal", "42,800.00", "kL", "Factory Consumption"],
        ["Recycled Effluent Water", "36,380.00", "kL", "85% Circular Recovery"],
        ["Hazardous Waste Generated", "4,200.00", "kg", "TSDF Authorized Disposal"]
    ]
    t_r = Table(r_data, colWidths=[180, 110, 80, 170])
    t_r.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#047857')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0FDF4')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_r)
    story.append(PageBreak())

    # PAGE 3: Carbon & Climate Footprint
    story.append(Paragraph("<b>Section 2: Carbon Footprint & Scope 1/2 Greenhouse Gas Emissions</b>", head_style))
    story.append(Spacer(1, 8))

    c_data = [
        ["Emissions Source", "Activity Parameter", "Calculated GHG", "Standard Protocol"],
        ["Scope 1 Direct GHG Emissions", "Diesel DG Sets & Fleet", "7.50", "tCO2e"],
        ["Scope 2 Indirect GHG Emissions", "Purchased Electricity (340,000 kWh)", "58.40", "tCO2e"],
        ["Total Operational GHG Footprint", "Consolidated Scope 1 + Scope 2", "65.90", "tCO2e"]
    ]
    t_c = Table(c_data, colWidths=[170, 160, 100, 110])
    t_c.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_c)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Compliance Declaration:</b> The facility maintains active ISO 14001:2015 accreditation and adheres strictly to the statutory guidelines prescribed by the State Pollution Control Board.", body_style))
    doc.build(story)

# -------------------------------------------------------------
# 07 SCANNED DOCUMENTS (Image-based PDF for OCR testing)
# -------------------------------------------------------------
def gen_14_scanned_fuel():
    path = os.path.join(BASE_DIR, "07_scanned_documents", "14_scanned_fuel_receipt.pdf")
    img_width, img_height = 800, 1000
    img = Image.new('RGB', (img_width, img_height), color=(245, 243, 238))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(25, 25), (img_width - 25, img_height - 25)], outline=(190, 185, 170), width=2)
    
    lines = [
        "========================================================",
        "          HIGHWAY AUTO SERVICE FUEL DISPATCH            ",
        "              (SCANNED CASH RECEIPT MEMO)               ",
        "========================================================",
        "",
        "CUSTOMER: Shree Balaji Components Pvt. Ltd.",
        "DATE: 2024-10-15",
        "RECEIPT NO: FL-SCAN-2024-7741",
        "",
        "--------------------------------------------------------",
        "ITEM DESCRIPTION           QTY        RATE      TOTAL   ",
        "--------------------------------------------------------",
        "High Speed Diesel (HSD)   450.0 L    91.25    41,062.50 ",
        "--------------------------------------------------------",
        "NET TOTAL PAID (INR):                       41,062.50   ",
        "",
        "Fuel Category: Diesel",
        "Vehicle Reg: GJ-01-AX-9912",
        "Status: Paid in Cash / Verified at Dispenser Pump #4",
        "",
        "Authorized Signature & Stamp: [AUTHENTICATED]"
    ]
    y = 60
    for l in lines:
        draw.text((50, y), l, fill=(40, 40, 45))
        y += 26

    # Stamp box
    draw.rectangle([(480, 700), (700, 820)], outline=(160, 60, 60), width=2)
    draw.text((500, 730), "SCANNED PETRO RECEIPT", fill=(160, 60, 60))
    draw.text((530, 765), "PUMP 04 VERIFIED", fill=(160, 60, 60))

    img.save(path, "PDF", resolution=100.0)

def gen_15_low_quality_scanned_waste():
    path = os.path.join(BASE_DIR, "07_scanned_documents", "15_low_quality_scanned_waste_manifest.pdf")
    img_width, img_height = 800, 1000
    img = Image.new('RGB', (img_width, img_height), color=(235, 230, 220))
    draw = ImageDraw.Draw(img)

    lines = [
        "FORM 10 - HAZARDOUS WASTE MANIFEST LOG",
        "GENERATOR: Narmada Chemical Products",
        "LOCATION: Ankleshwar Industrial Area",
        "MANIFEST NO: WM-SCAN-9912",
        "DATE: 2024-09-28",
        "---------------------------------------------------",
        "WASTE STREAM                    QUANTITY   UNIT    ",
        "---------------------------------------------------",
        "Chemical Treatment Sludge       1,250.0    KG      ",
        "Spent Industrial Solvent          350.0    LITERS  ",
        "Contaminated Packaging Scrap      180.0    KG      ",
        "---------------------------------------------------",
        "TSDF FACILITY: Enviro Waste Solutions",
        "COMPLIANCE: Hazardous Waste Rules 2016"
    ]
    y = 80
    for l in lines:
        draw.text((60, y), l, fill=(70, 70, 75))
        y += 32

    # Add noise and slight rotation
    img = img.rotate(1.2, resample=Image.BILINEAR, fillcolor=(235, 230, 220))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))
    img.save(path, "PDF", resolution=90.0)

# -------------------------------------------------------------
# 08 EDGE CASES
# -------------------------------------------------------------
def gen_16_ambiguous_electricity_invoice():
    path = os.path.join(BASE_DIR, "08_edge_cases", "16_ambiguous_electricity_invoice.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("GRID POWER SUPPLY CORP — COMMERCIAL TAX INVOICE", title_style),
        Paragraph("Monthly Industrial Power Tariff & Energy Docket", ParagraphStyle('S', parent=styles['Normal'], fontSize=9, alignment=1)),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Customer Name:</b> Tara Engineering Works", body_style), Paragraph("<b>Invoice No:</b> GPC-INV-2024-771", body_style)],
        [Paragraph("<b>Meter Serial:</b> HT-MTR-8812", body_style), Paragraph("<b>Billing Month:</b> November 2024", body_style)],
        [Paragraph("<b>Tariff Code:</b> HT-Industrial 11kV", body_style), Paragraph("<b>Contract Demand:</b> 150 kVA", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    item_data = [
        ["Line Description", "HSN/SAC", "Quantity", "Unit", "Amount (INR)"],
        ["Electrical Energy Supply Units", "27160000", "35,000.00", "kWh", "245,000.00"],
        ["Peak Billed Demand Charge", "998719", "120.00", "kVA", "42,000.00"],
        ["GST Statutory Duty (18%)", "-", "-", "-", "51,660.00"],
        ["Net Invoice Total Payable", "-", "-", "-", "INR 338,660.00"]
    ]
    t_item = Table(item_data, colWidths=[170, 70, 70, 60, 170])
    t_item.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_item)
    doc.build(story)

def gen_17_unknown_correspondence():
    path = os.path.join(BASE_DIR, "08_edge_cases", "17_unknown_correspondence.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("DYNAMIC BUSINESS ALLIANCE — CORRESPONDENCE MEMO", title_style),
        Spacer(1, 14),
        Paragraph("<b>Date:</b> 12th October 2024", body_style),
        Paragraph("<b>To:</b> Vendor Relations Committee, Tara Engineering Works", body_style),
        Paragraph("<b>Subject:</b> Annual Trade Expo Participation & Office Stationery Quotation", body_style),
        Spacer(1, 10),
        Paragraph("Dear Sir / Madam,", body_style),
        Spacer(1, 6),
        Paragraph("We refer to the discussions held at the Industrial Trade Summit in Mumbai regarding supply of 500 conference folders and 250 registration badges under reference PO-441299. Please confirm your delegate registration numbers at the earliest.", body_style),
        Spacer(1, 8),
        Paragraph("Total estimated exhibition fee: INR 45,000.00 payable by bank draft.", body_style),
        Spacer(1, 14),
        Paragraph("Sincerely,<br/>General Secretary, Trade Alliance", body_style),
    ]
    doc.build(story)

def gen_18_adversarial_numeric():
    path = os.path.join(BASE_DIR, "08_edge_cases", "18_adversarial_numeric_docket.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E1B4B'), alignment=1)
    body_style = ParagraphStyle('B1', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))

    story = [
        Paragraph("BHARAT HEAVY ENGINEERING MSME INVOICE DOCKET", title_style),
        Spacer(1, 10),
    ]

    h_data = [
        [Paragraph("<b>Company:</b> Bharat Heavy Engineering Pvt. Ltd.", body_style), Paragraph("<b>Purchase Order:</b> PO-998877", body_style)],
        [Paragraph("<b>Meter Number:</b> 100000", body_style), Paragraph("<b>HSN Code:</b> 27160000", body_style)],
        [Paragraph("<b>Billing Month:</b> October 2024", body_style), Paragraph("<b>Invoice Date:</b> 2024-10-15", body_style)]
    ]
    t_h = Table(h_data, colWidths=[270, 270])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 10))

    item_data = [
        ["Line Item Description", "Reference Code", "Quantity", "Unit", "Total Charge (INR)"],
        ["Grid Electricity Supply", "HSN 27160000", "100,000.00", "kWh", "72,000.00"],
        ["Diesel Generator Backup Fuel", "HSN 27101930", "1,000.00", "Liters", "10,000.00"],
        ["Applicable GST Tax (18%)", "Statutory Tax", "-", "-", "18,000.00"],
        ["Net Invoice Total Payable Amount", "Total Due", "-", "-", "INR 1,00,000.00"]
    ]
    t_item = Table(item_data, colWidths=[170, 90, 80, 60, 140])
    t_item.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#312E81')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EEF2FF')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_item)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Notice: This commercial docket contains zero information regarding water usage or waste management.</i>", body_style))
    doc.build(story)

def main():
    print("Generating 18 validation dataset documents...")
    gen_01_clean_electricity()
    gen_02_indian_format_electricity()
    gen_03_missing_fields_electricity()
    gen_04_clean_fuel()
    gen_05_confusing_numbers_fuel()
    gen_06_industrial_water()
    gen_07_missing_recycled_water()
    gen_08_material_invoice()
    gen_09_indian_format_invoice()
    gen_10_sustainability_materials_invoice()
    gen_11_clean_waste_manifest()
    gen_12_missing_quantities_waste()
    gen_13_multipage_esg()
    gen_14_scanned_fuel()
    gen_15_low_quality_scanned_waste()
    gen_16_ambiguous_electricity_invoice()
    gen_17_unknown_correspondence()
    gen_18_adversarial_numeric()
    print("Successfully generated all 18 documents.")

if __name__ == "__main__":
    main()
