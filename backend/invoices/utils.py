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
    styles.add(ParagraphStyle(name='InvoiceTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#9A1D56'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='InvoiceHeader', parent=styles['Normal'], fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='InvoiceHeaderRight', parent=styles['Normal'], fontSize=10, leading=14, alignment=2)) # Right align
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading3'], fontSize=12, spaceAfter=6, fontName='Helvetica-Bold'))
    
    order = invoice.order
    currency = order.currency

    # Determine Layout
    template_type = getattr(order, 'invoice_template', 'default')
    
    if template_type == 'awb':
        _draw_awb_layout(elements, styles, invoice, order, currency)
    else:
        _draw_default_layout(elements, styles, invoice, order, currency)
    
    # Build
    doc.build(elements)
    
    # Save
    # Naming: Customer_Branch_Order (if branch) or Customer_Order
    c_name = order.customer.name.replace(' ', '')
    b_name = order.branch.name.replace(' ', '') if order.branch else None
    inv_code = invoice.invoice_code
    
    if b_name:
        filename = f"{c_name}_{b_name}_{inv_code}.pdf"
    else:
        filename = f"{c_name}_{inv_code}.pdf"
    
    if invoice.pdf_file:
        try:
            old_path = invoice.pdf_file.path
            if os.path.isfile(old_path):
                os.remove(old_path)
        except Exception:
            pass
            
    invoice.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=True)
    return True

def _draw_default_layout(elements, styles, invoice, order, currency):
    # ... (Moved existing logic here) ...
    customer = order.customer
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
    
    header_data = [[
        Image(logo_path, width=3.5*cm, height=3.5*cm) if os.path.exists(logo_path) else "",
        Table(company_info, style=[('VALIGN', (0,0), (-1,-1), 'TOP')]),
        Table(location_info, style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
    ]]
    
    header_table = Table(header_data, colWidths=[4.5*cm, 8.5*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#9A1D56')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 1*cm))
    
    # Invoice Details box
    invoice_date = order.date
    if isinstance(invoice_date, str):
        try:
            from dateutil import parser
            invoice_date = parser.parse(invoice_date)
        except:
            pass
    date_str = invoice_date.strftime('%d %b, %Y') if hasattr(invoice_date, 'strftime') else str(invoice_date)
    
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
        c_details.append([Spacer(1, 0.2*cm)])
        c_details.append([Paragraph("<b>Remarks</b>", styles['SectionTitle'])])
        c_details.append([Paragraph(f"{order.remarks}", styles['Normal'])])

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
    
    # Items
    items_data = [[
        'Item Detail', 'Length\n(CM)', 'Boxes', 'Stems\nPer Box', 'Total\nStems', 'Price\nPer Stem', 'Amount'
    ]]
    
    for item in order.items.all():
        items_data.append([
            Paragraph(item.product.name, styles['Normal']),
            item.stem_length_cm,
            item.boxes,
            item.stems_per_box,
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
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('TOPPADDING', (0,0), (-1,0), 12),
        
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('ALIGN', (5,1), (6,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
        
        ('LEFTPADDING', (0,0), (0,-1), 6),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Totals
    totals_data = [
        ['Subtotal', f"{currency} {order.subtotal_amount()}"],
        ['Logistics / Other Costs', f"{currency} {order.logistics_cost or '0.00'}"],
        ['Total', f"{currency} {order.total_amount}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[14*cm, 5*cm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('TEXTCOLOR', (0,0), (0,-1), colors.grey),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (-1,-1), (-1,-1), colors.HexColor('#9A1D56')),
        ('FONTSIZE', (-1,-1), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(totals_table)
    
    # Footer
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("We bloom for you", ParagraphStyle(name='FooterTags', parent=styles['Normal'], alignment=1, textColor=colors.grey)))
    elements.append(Paragraph("www.zaharaflowers.com", ParagraphStyle(name='FooterWeb', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.grey)))

def _draw_awb_layout(elements, styles, invoice, order, currency):
    """AWB / Export Invoice Layout"""
    from reportlab.platypus import Paragraph
    
    # 1. Header (Centered, no logo image needed as per scratch, but let's keep text clean)
    # 1. Header (Centered, no logo image needed as per scratch, but let's keep text clean)
    header_style = ParagraphStyle(name='AWBHeader', parent=styles['Heading1'], alignment=1, fontSize=16, fontName='Helvetica-Bold', spaceAfter=10)
    sub_style = ParagraphStyle(name='AWBSub', parent=styles['Normal'], alignment=1, fontSize=10, spaceAfter=8)
    link_style = ParagraphStyle(name='AWBLink', parent=styles['Normal'], alignment=1, fontSize=10, textColor=colors.blue, spaceAfter=8)
    
    elements.append(Paragraph("ZAHARA FLOWERS LIMITED", header_style))
    elements.append(Paragraph("P.O. BOX 9668-20100, NAKURU - KENYA", sub_style))
    elements.append(Paragraph("<u>lucy@zaharaflowers.com</u>", link_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # "INVOICE" Title Box
    # We can use a table to create the thick border box affect
    title_data = [[Paragraph("INVOICE", ParagraphStyle(name='TitleC', alignment=1, fontSize=14, fontName='Helvetica-Bold'))]]
    title_table = Table(title_data, colWidths=[19*cm])
    title_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(title_table)
    
    # 2. Details Box (Consignee | Deliver To | Info)
    # 3 Columns
    # Col 1: Consignee Header + Data
    # Col 2: Deliver To Header + Data
    # Col 3: Invoice Meta Data
    
    customer = order.customer
    invoice_date = order.date
    if isinstance(invoice_date, str):
        try: from dateutil import parser; invoice_date = parser.parse(invoice_date)
        except: pass
    date_str = invoice_date.strftime('%d-%b-%y') if hasattr(invoice_date, 'strftime') else str(invoice_date)
    
    # Styles
    # Styles
    label_s = ParagraphStyle(name='Label', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold')
    val_s = ParagraphStyle(name='Val', parent=styles['Normal'], fontSize=11, textColor=colors.red)
    # Let's use red for the variable data as seen in screenshot (Consignee Name etc seem red)
    
    # Col 3 Data
    # Col 3 Data
    # To fix "Right side of the top row... Label and Value on separate columns"
    # We will make col3_table have 2 distinct columns.
    
    col3_data = [
        [Paragraph('<b>Invoice No:</b>', styles['Normal']), Paragraph(f"{invoice.invoice_code}", styles['Normal'])],
        [Paragraph('<b>PIN NO:</b>', styles['Normal']), Paragraph('P052064981H', styles['Normal'])],
        [Paragraph('<b>Date:</b>', styles['Normal']), Paragraph(f"{date_str}", styles['Normal'])],
        [Paragraph('<b>Agent:</b>', styles['Normal']), Paragraph(f"{order.agent_name or 'TTC'}", styles['Normal'])],
        [Paragraph('<b>Flight No:</b>', styles['Normal']), Paragraph(f"{order.flight_number or ''}", styles['Normal'])],
        [Paragraph('<b>AWB No:</b>', styles['Normal']), Paragraph(f"{order.awb_number or ''}", styles['Normal'])],
        [Paragraph('<b>Mode of transport:</b>', styles['Normal']), Paragraph(f"{order.mode_of_transport or 'AIR'}", styles['Normal'])],
        [Paragraph('<b>INCO Term:</b>', styles['Normal']), Paragraph(f"{order.inco_term or 'FOB'}", styles['Normal'])],
    ]
    # Formatting right column table
    col3_table = Table(col3_data, colWidths=[2.8*cm, 3.2*cm]) # Split width 
    col3_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'RIGHT'), # Labels right aligned
        ('ALIGN', (1,0), (1,-1), 'RIGHT'), # Values right aligned
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Consignee/Deliver To Content
    consignee_content = [
        Paragraph(customer.name, val_s),
        # Add address/phone if we had them. For now just name.
    ]
    
    deliver_to_content = [
        Paragraph(order.deliver_to or order.branch.name if order.branch else "TTC", val_s),
    ]
    
    # Master Table for Details
    # Row 1: Headers
    # Row 2: Content
    
    # Actually, ReportLab tables are grid based.
    # Col 1 (Consignee), Col 2 (Deliver To), Col 3 (Empty/Spacer), Col 4 (Meta)
    
    # Let's try to mimic the screenshot's grid lines exactly.
    # | Consignee: [Label] | Deliver To: [Label] | [Empty] | Invoice No: ... |
    # | [Data]             | [Data]              |         | PIN NO: ...     |
    
    # We'll use a nested table approach or just a carefully constructed single table.
    
    # Let's go with:
    # Col 1: Consignee Header (Cell 0,0) -> Data (Cell 0,1)
    # Col 2: Deliver To Header -> Data
    # Col 3: Spacer
    # Col 4: Meta info table
    
    # Wait, screenshot shows:
    # -----------------------------------------------------
    # | Consignee: | Deliver To: |      | Invoice No: ... |
    # | [Red Data] | [Red Data]  |      | ...             |
    # | ...        | ...         |      | ...             |
    # -----------------------------------------------------
    
    # Master Table for Details
    # Row 1: Content (Merged Label + Value)
    
    # Consignee Cell Content
    cons_content = [
        Paragraph('<b>Consignee:</b>', label_s),
        Spacer(1, 0.2*cm),
        Paragraph(f"{customer.name}", val_s)
    ]
    
    # Deliver To Cell Content
    del_content = [
        Paragraph('<b>Deliver To:</b>', label_s),
        Spacer(1, 0.2*cm),
        Paragraph(f"{order.deliver_to or (order.branch.name if order.branch else 'TTC')}", val_s)
    ]

    t_data = [
        [cons_content, del_content, '', col3_table]
    ]
    
    t = Table(t_data, colWidths=[5*cm, 5*cm, 3*cm, 6*cm])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, colors.black), # Thick Outer Border
        ('LINEAFTER', (0,0), (0,0), 1, colors.black), # Line after Consignee
        ('LINEAFTER', (1,0), (1,0), 1, colors.black), # Line after Deliver To
        ('LINEBEFORE', (3,0), (3,0), 1, colors.black), # Line before Meta Data
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    
    # 3. Items Table (AWB Style)
    # Headers: Varieties | Length (cm) | No. of Boxes | Qtty per Box | Total Stems | Price Per Stem | Total Price (EURO)
    
    # Note: Screenshot uses EURO, but we should use `currency`.
    
    items_header = [
        'Varieties', 'Length\n(cm)', 'No. of\nBoxes', 'Qtty per\nBox', 'Total Stems', 'Price Per\nStem', f'Total Price\n({currency})'
    ]
    
    items_data = [items_header]
    
    total_stems = 0
    total_boxes = 0
    
    for item in order.items.all():
        total_stems += item.stems
        total_boxes += item.boxes
        items_data.append([
            Paragraph(item.product.name, styles['Normal']),
            item.stem_length_cm,
            item.boxes,
            item.stems_per_box,
            item.stems,
            item.price_per_stem,
            f"{currency} {item.total_amount}"
        ])
        
    # Spacer rows to fill page? Screenshot shows many empty rows.
    # We'll add a few empty rows to mimic the look or just leave dynamic.
    # Let's add 5 empty rows for "look".
    for _ in range(5):
         items_data.append(['', '', '', '', '', '', '']) 
         
    # Total Row
    items_data.append([
        'TOTAL', '', total_boxes, '', total_stems, '', f"{currency} {order.total_amount}"
    ])
    
    t_items = Table(items_data, colWidths=[
        6*cm, 2*cm, 2*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm
    ])
    
    t_items.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black), # Thinner inner grid
        ('linebelow', (0,0), (-1,0), 1.5, colors.black), # Thick line below header
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Header Bold
        ('ALIGN', (1,0), (-1,-1), 'CENTER'), # Numbers centered
        ('ALIGN', (6,1), (6,-1), 'RIGHT'), # Prices right
        
        # Last Row Bold
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.whitesmoke),
    ]))
    elements.append(t_items)




