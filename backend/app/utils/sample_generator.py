import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont

def generate_sample_electricity_bill(output_path: str) -> str:
    """Generate a clean text MSME industrial electricity bill PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4B5563'),
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#111827')
    )
    
    story = []
    
    story.append(Paragraph("STATE ELECTRICITY DISTRIBUTION CORPORATION", title_style))
    story.append(Paragraph("Industrial & MSME High-Tension (HT) Tariff Invoice", subtitle_style))
    story.append(Spacer(1, 12))
    
    # Header Info Table
    header_data = [
        [
            Paragraph("<b>Consumer Name:</b> Apex Precision Forgings Pvt. Ltd.", body_style),
            Paragraph("<b>Bill Number:</b> HT-2024-OCT-8891", body_style)
        ],
        [
            Paragraph("<b>GSTIN / Udyam:</b> 27AABCA1234F1Z8 / UDYAM-MH-12-00451", body_style),
            Paragraph("<b>Billing Month:</b> October 2024", body_style)
        ],
        [
            Paragraph("<b>Facility Address:</b> Plot B-12, MIDC Industrial Area, Pune 411018", body_style),
            Paragraph("<b>Issue Date:</b> 2024-11-02", body_style)
        ],
        [
            Paragraph("<b>Industry Sector:</b> Precision Metal Forging & Auto Components", body_style),
            Paragraph("<b>Billing Period:</b> 2024-10-01 to 2024-10-31", body_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[270, 270])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    
    # Energy Consumption Summary
    story.append(Paragraph("<b>1. Energy & Power Consumption Metrics</b>", section_style))
    metrics_data = [
        ["Parameter", "Recorded Value", "Unit", "Benchmark / Status"],
        ["Total Active Energy Consumption", "124,500.00", "kWh", "Normal Operation"],
        ["Renewable Solar Captive Generation", "18,200.00", "kWh", "14.6% Solar Share"],
        ["Net Grid Electricity Import", "106,300.00", "kWh", "Billed Import"],
        ["Recorded Peak Demand", "342.50", "kVA", "Sanctioned: 400 kVA"],
        ["Average Power Factor (PF)", "0.98", "Lagging", "Incentive Eligible (>0.95)"],
        ["Diesel Generator Backup Fuel Used", "1,250.00", "Liters", "12.5 hrs outage"],
    ]
    t_metrics = Table(metrics_data, colWidths=[200, 110, 80, 150])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 10))
    
    # Carbon Footprint Estimates
    story.append(Paragraph("<b>2. Sustainability & Carbon Emissions Estimate</b>", section_style))
    carbon_data = [
        ["Emissions Source", "Activity Level", "Emission Factor", "Total tCO2e"],
        ["Scope 1 - Diesel Generators (HSD)", "1,250 Liters", "2.68 kg CO2e/L", "3.35 tCO2e"],
        ["Scope 2 - Grid Purchased Electricity", "106,300 kWh", "0.71 kg CO2e/kWh", "75.47 tCO2e"],
        ["Solar Avoided Emissions", "18,200 kWh", "0.71 kg CO2e/kWh", "-12.92 tCO2e (Offset)"],
        ["Net Total Carbon Footprint", "-", "-", "78.82 tCO2e"]
    ]
    t_carbon = Table(carbon_data, colWidths=[180, 120, 130, 110])
    t_carbon.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#047857')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0FDF4')]),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_carbon)
    story.append(Spacer(1, 10))
    
    # Financial Tariff Line Items
    story.append(Paragraph("<b>3. Billing Line Items & Charges</b>", section_style))
    line_data = [
        ["Line Item Description", "Qty / Units", "Rate (INR)", "Total Amount (INR)"],
        ["Energy Charges (Grid Units)", "106,300 kWh", "7.25 / kWh", "770,675.00"],
        ["Fixed Demand Charges", "342.50 kVA", "350.00 / kVA", "119,875.00"],
        ["Fuel Surcharge Adjustment (FAC)", "106,300 kWh", "0.45 / kWh", "47,835.00"],
        ["Power Factor Incentive Rebate", "-", "-", "-15,413.50"],
        ["Electricity Duty & Green Cess (9%)", "-", "-", "82,977.44"],
        ["Net Total Payable Amount", "-", "-", "INR 1,005,948.94"]
    ]
    t_line = Table(line_data, colWidths=[200, 110, 100, 130])
    t_line.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FEF3C7')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_line)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Compliance & Environmental Flags:</b> Unit compliant with State Pollution Control Board guidelines. ISO 50001 Energy Management standard active. Power factor bonus achieved.", body_style))
    
    doc.build(story)
    return output_path

def generate_sample_esg_audit_report(output_path: str) -> str:
    """Generate a clean text multi-parameter MSME ESG & Sustainability Audit Report PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=17,
        leading=21,
        textColor=colors.HexColor('#065F46'),
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151'),
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1F2937'),
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#111827')
    )
    
    story = []
    story.append(Paragraph("GREEN ECO TEXTILES & APPAREL PVT. LTD.", title_style))
    story.append(Paragraph("Annual ESG & Sustainability Compliance Audit Report - FY2023-24", subtitle_style))
    story.append(Spacer(1, 12))
    
    # Metadata Table
    meta_data = [
        [Paragraph("<b>Company:</b> Green Eco Textiles Pvt. Ltd.", body_style), Paragraph("<b>Audit Standard:</b> ISO 14001:2015 & ZED Gold MSME", body_style)],
        [Paragraph("<b>Facility:</b> Tirupur Garment Processing Cluster", body_style), Paragraph("<b>Reporting Period:</b> 2023-04-01 to 2024-03-31", body_style)],
        [Paragraph("<b>Auditor:</b> EcoCert International Ltd.", body_style), Paragraph("<b>Compliance Status:</b> Compliant (Zero High-Risk Flags)", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ECFDF5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#A7F3D0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1FAE5')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))
    
    # Water & Effluent Management
    story.append(Paragraph("<b>1. Water Consumption & Effluent Recycling</b>", section_style))
    water_data = [
        ["Metric Description", "Annual Quantity", "Unit", "Recovery / Target"],
        ["Freshwater Municipal Withdrawal", "42,800.00", "kL (cubic meters)", "Specific: 45 L/kg fabric"],
        ["Zero Liquid Discharge (ZLD) Recycled Water", "36,380.00", "kL", "85.0% Recycling Rate"],
        ["Rainwater Harvesting Capacity", "8,500.00", "kL", "100% recharged to aquifer"],
        ["Biological Sludge Generated", "4,200.00", "kg", "Sent to Authorized TSDF"]
    ]
    t_water = Table(water_data, colWidths=[200, 110, 110, 120])
    t_water.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0F9FF')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_water)
    story.append(Spacer(1, 8))
    
    # Waste & Circular Economy
    story.append(Paragraph("<b>2. Solid Waste & Circularity Metrics</b>", section_style))
    waste_data = [
        ["Waste Stream", "Annual Generated", "Unit", "Disposal / Recycling Method"],
        ["Fabric Cutting Scraps (Cotton)", "52,400.00", "kg", "Recycled to Open-End Yarn (100%)"],
        ["Polyester / Synthetic Trims", "14,800.00", "kg", "Downcycled / Secondary insulation"],
        ["Hazardous Chemical Packaging", "1,850.00", "kg", "Hazardous Waste Manifest Rule 9"],
        ["Overall Waste Diversion Rate", "88.50", "%", "Benchmark Target: 85%"]
    ]
    t_waste = Table(waste_data, colWidths=[180, 110, 80, 170])
    t_waste.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#D97706')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FFFBEB')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_waste)
    story.append(Spacer(1, 8))
    
    # Energy & Carbon Footprint
    story.append(Paragraph("<b>3. Energy Profile & Scope 1, 2, 3 Emissions</b>", section_style))
    energy_data = [
        ["Emissions Category", "Source", "Consumption", "Emissions (tCO2e)"],
        ["Scope 1 Direct", "Biomass Briquette Boiler (Process Steam)", "180 MT Briquettes", "14.20 tCO2e"],
        ["Scope 1 Direct", "Diesel Emergency Generator Backup", "2,800 Liters HSD", "7.50 tCO2e"],
        ["Scope 2 Indirect", "Grid Electricity (Wind Power PPA 60%)", "340,000 kWh", "96.56 tCO2e"],
        ["Total Operational GHG", "Scope 1 + Scope 2 Consolidated", "-", "118.26 tCO2e"]
    ]
    t_energy = Table(energy_data, colWidths=[130, 180, 120, 110])
    t_energy.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4338CA')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_energy)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>Key Findings & Recommendations:</b> 1) Solar rooftop expansion of 150 kW recommended. 2) Excellent zero liquid discharge compliance maintained throughout FY2023-24. 3) ISO 14001:2015 and OEKO-TEX Standard 100 recertification approved.", body_style))
    
    doc.build(story)
    return output_path

def generate_sample_scanned_receipt_pdf(output_path: str) -> str:
    """
    Generate an image-only scanned PDF to specifically trigger and test OCR fallback!
    This embeds an image containing text without standard PDF text objects.
    """
    img_width, img_height = 800, 1050
    image = Image.new('RGB', (img_width, img_height), color=(248, 246, 240))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([(20, 20), (img_width - 20, img_height - 20)], outline=(180, 175, 160), width=2)
    
    lines = [
        "============================================================",
        "          INDUSTRIAL FUEL & WASTE LOG MANIFEST              ",
        "           (SCANNED DISPATCH RECEIPT - COPY 2)             ",
        "============================================================",
        "",
        "CUSTOMER: Shree Balaji Polymers & Auto Moulds MSME",
        "REG ID: UDYAM-GJ-01-998822 | GSTIN: 24AAACB9012D1ZX",
        "SITE: GIDC Estate, Phase II, Vatva, Ahmedabad, Gujarat",
        "DATE OF DISPATCH: 2024-09-15",
        "RECEIPT NO: FL-WST-2024-4410",
        "",
        "------------------------------------------------------------",
        "ITEM DESCRIPTION               QTY       UNIT       AMOUNT  ",
        "------------------------------------------------------------",
        "High Speed Diesel (HSD)        3,400.0   LITERS     319,600 ",
        "Industrial Furnace Fuel Oil     1,200.0   LITERS     102,000 ",
        "Scrap Plastic Polymer Flakes   8,500.0   KG          68,000 ",
        "Used Lubricant Oil (Hazardous)   450.0   LITERS      18,000 ",
        "Hazardous Waste Treatment Fee      1.0   CHARGE      15,000 ",
        "------------------------------------------------------------",
        "TOTAL INVOICE VALUE:                      INR 522,600.00",
        "",
        "SUSTAINABILITY & EMISSIONS METRICS:",
        "- Fuel Diesel Scope 1 Direct Emissions: 9.11 tCO2e",
        "- Waste Polymer Recycled: 8,500 kg (100% circular)",
        "- Hazardous Used Oil Handled: 450 Liters via CPCB certified recycler",
        "- Compliance Status: Compliant with Hazardous Waste Rules 2016",
        "- Applicable Certifications: ISO 9001, ISO 14001",
        "",
        "Authorized Signatory & Weighbridge Stamp: [VERIFIED OK]"
    ]
    
    y = 40
    for line in lines:
        draw.text((45, y), line, fill=(30, 30, 35))
        y += 24
        
    draw.rectangle([(500, 750), (720, 850)], outline=(180, 50, 50), width=3)
    draw.text((515, 780), "AUTHENTICATED OCR SCAN", fill=(180, 50, 50))
    draw.text((535, 810), "CPCB AUDIT PASS", fill=(180, 50, 50))
    
    image.save(output_path, "PDF", resolution=100.0)
    return output_path

def generate_sample_adversarial_invoice(output_path: str) -> str:
    """
    Generate an Adversarial Test PDF containing ambiguous numbers:
    - Invoice monetary amount: ₹1,00,000.00 (INR)
    - Electricity consumption: 100,000.00 kWh
    - Fuel quantity: 1,000.00 Liters
    - Unrelated numbers: Purchase Order PO-998877, HSN Code 27160000, Tax ₹18,000.00
    - Missing water info (No mention of water)
    - Missing waste info (No mention of waste)
    - Compliance status: Not mentioned anywhere
    
    Tests that:
    1. System does NOT confuse monetary amount ₹1,00,000 with 100,000 kWh or 1,000 L fuel.
    2. Missing water_consumption_kl and waste quantities remain strictly null.
    3. Missing compliance_status remains null instead of inventing "Compliant".
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E1B4B'),
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    
    story = []
    story.append(Paragraph("BHARAT HEAVY ENGINEERING MSME INVOICE", title_style))
    story.append(Paragraph("Commercial & Utility Supply Manifest -- ADVERSARIAL TEST DOCKET", subtitle_style))
    story.append(Spacer(1, 10))
    
    header_data = [
        [Paragraph("<b>Company:</b> Bharat Heavy Engineering Pvt. Ltd.", body_style), Paragraph("<b>Purchase Order:</b> PO-998877", body_style)],
        [Paragraph("<b>GSTIN:</b> 27AAACB5544R1Z3", body_style), Paragraph("<b>Invoice Date:</b> 2024-10-15", body_style)],
        [Paragraph("<b>HSN Code:</b> 27160000 (Electrical Energy)", body_style), Paragraph("<b>Billing Month:</b> October 2024", body_style)]
    ]
    t_header = Table(header_data, colWidths=[270, 270])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>1. Detailed Quantities & Tariff Line Items</b>", section_style))
    table_data = [
        ["Item Description", "HSN / Item Ref", "Quantity", "Unit", "Total Charge (INR)"],
        ["Grid Electricity Supply", "HSN 27160000", "100,000.00", "kWh", "75,000.00"],
        ["High Speed Diesel (HSD) Fuel Supply", "HSN 27101930", "1,000.00", "Liters", "10,000.00"],
        ["Generator Maintenance & Tariff Service", "HSN 998719", "1.00", "Service", "15,000.00"],
        ["Net Invoice Total Payable Amount", "-", "-", "-", "INR 1,00,000.00"]
    ]
    t_table = Table(table_data, colWidths=[170, 90, 90, 65, 125])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#312E81')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EEF2FF')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Note:</b> Net Payable Invoice Value is Rs. 1,00,000.00. Applicable GST Tax @ 18% included (INR 18,000.00).", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<i>Notice: This commercial docket contains zero information regarding water usage or waste management.</i>", body_style))
    
    doc.build(story)
    return output_path
