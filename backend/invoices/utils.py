import os
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm

def generate_invoice_pdf(invoice):
    """Generate PDF for an invoice using ReportLab (Robust & Portable)"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1*cm, leftMargin=1*cm,
                            topMargin=1*cm, bottomMargin=1*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(name='InvoiceTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#9A1D56')))
    styles.add(ParagraphStyle(name='InvoiceHeader', parent=styles['Normal'], fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='InvoiceHeaderRight', parent=styles['Normal'], fontSize=10, leading=14, alignment=2)) # Right align
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading3'], fontSize=12, spaceAfter=6))
    
    # 1. Header Section
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
    
    # Company Info
    company_info = [
        [Paragraph("<b>Zahara Flowers Ltd</b>", styles['InvoiceTitle'])],
        [Paragraph("www.zaharaflowers.com", styles['InvoiceHeader'])],
        [Paragraph("info@zaharaflowers.com", styles['InvoiceHeader'])],
        [Paragraph("+254 725 750 057", styles['InvoiceHeader'])]
    ]
    
    # Location Info
    location_info = [
        [Paragraph("Nakuru & Laikipia, Kenya", styles['InvoiceHeaderRight'])],
        [Paragraph("TAX ID P052064981H", styles['InvoiceHeaderRight'])]
    ]
    
    # Header Table layout
    header_data = [[
        Image(logo_path, width=3*cm, height=3*cm) if os.path.exists(logo_path) else "",
        Table(company_info, style=[('VALIGN', (0,0), (-1,-1), 'TOP')]),
        Table(location_info, style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
    ]]
    
    header_table = Table(header_data, colWidths=[4*cm, 9*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#9A1D56')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 1*cm))
    
    # 2. Invoice Details (Gray Box)
    order = invoice.order
    customer = order.customer
    currency = order.currency
    
    # Handle date safely (could be string if coming directly from form save)
    invoice_date = order.date
    if isinstance(invoice_date, str):
        try:
            from dateutil import parser
            invoice_date = parser.parse(invoice_date)
        except:
            pass

    date_str = invoice_date.strftime('%d %b, %Y') if hasattr(invoice_date, 'strftime') else str(invoice_date)
    
    # Left Column: Consignee
    c_details = [
        [Paragraph("<b>Invoice Number</b>", styles['SectionTitle'])],
        [Paragraph(f"#{invoice.invoice_code}", styles['Normal'])],
        [Spacer(1, 0.2*cm)],
        [Paragraph("<b>Invoice Date</b>", styles['SectionTitle'])],
        [Paragraph(f"{date_str}", styles['Normal'])],
        [Spacer(1, 0.2*cm)],
        [Paragraph("<b>Consignee Details</b>", styles['SectionTitle'])],
        [Paragraph(f"{customer.name}", styles['Normal'])],
    ]
    if order.branch:
         c_details.append([Paragraph(f"Branch: {order.branch.name}", styles['Normal'])])
    if order.remarks:
        c_details.append([Spacer(1, 0.1*cm)])
        c_details.append([Paragraph(f"Remarks: {order.remarks}", styles['Normal'])])

    # Center Column: Account Details
    acc_no = "(USD Acc) 0112397355003"
    if currency == 'EUR': acc_no = "(EURO Ac) 0112397355002"
    elif currency == 'KSH': acc_no = "(Ksh Acc.) 0112397355001"
    
    bank_details = [
        [Paragraph("<b>Account Details</b>", styles['SectionTitle'])],
        [Paragraph(f"<b>Acc No:</b> {acc_no}", styles['Normal'])],
        [Paragraph("<b>Bank Name:</b> SBM Bank", styles['Normal'])],
        [Paragraph("<b>Swift Code:</b> SBMKKENAXXX", styles['Normal'])],
        [Paragraph("<b>Bank Code:</b> 60", styles['Normal'])],
        [Paragraph("<b>Branch Code:</b> 011", styles['Normal'])],
    ]
    
    # Right Column: Total
    total_details = [
         [Paragraph(f"<b>Invoice of ({currency})</b>", styles['SectionTitle'])],
         [Paragraph(f"<font color='#9A1D56' size=18><b>{currency} {order.total_amount}</b></font>", styles['Normal'])],
    ]

    details_table_data = [[
        Table(c_details),
        Table(bank_details),
        Table(total_details)
    ]]
    
    details_table = Table(details_table_data, colWidths=[6.3*cm, 6.3*cm, 6.3*cm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 1*cm))
    
    # 3. Items Table
    items_data = [[
        'Item Detail', 'Length\n(CM)', 'Stems\nPer Box', 'Boxes', 'Total\nStems', 'Price\nPer Stem', 'Amount'
    ]]
    
    for item in order.items.all():
        items_data.append([
            Paragraph(item.product.name, styles['Normal']),
            item.stem_length_cm,
            item.stems_per_box,
            item.boxes,
            item.stems,
            f"{currency} {item.price_per_stem}",
            f"{currency} {item.total_amount}"
        ])
        
    items_table = Table(items_data, colWidths=[6*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.dimgrey),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
        
        ('ALIGN', (1,1), (-1,-1), 'CENTER'), # Center numbers
        ('ALIGN', (5,1), (6,-1), 'RIGHT'), # Right align prices
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        
        ('LEFTPADDING', (0,0), (0,-1), 6), # Align left for Product
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 4. Totals
    totals_data = [
        ['Subtotal', f"{currency} {order.subtotal_amount()}"],
        ['Logistics / Other Costs', f"{currency} {order.logistics_cost or '0.00'}"],
        ['Total', f"{currency} {order.total_amount}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[14*cm, 5*cm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('TEXTCOLOR', (0,0), (0,-1), colors.grey),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.lightgrey), # Lines until last row
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (-1,-1), (-1,-1), colors.HexColor('#9A1D56')),
        ('FONTSIZE', (-1,-1), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 2*cm))
    
    # 5. Footer
    elements.append(Paragraph("We bloom for you", ParagraphStyle(name='FooterTags', parent=styles['Normal'], alignment=1, textColor=colors.grey)))
    elements.append(Paragraph("www.zaharaflowers.com", ParagraphStyle(name='FooterWeb', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.grey)))
    
    # Build
    doc.build(elements)
    
    # Save
    filename = f"{invoice.invoice_code}.pdf"
    
    if invoice.pdf_file:
        try:
            old_path = invoice.pdf_file.path
            if os.path.isfile(old_path):
                os.remove(old_path)
        except Exception:
            pass
            
    invoice.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=True)
    return True



