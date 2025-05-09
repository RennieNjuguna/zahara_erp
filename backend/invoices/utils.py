from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from orders.models import Order
from datetime import datetime

def generate_account_statement_pdf(statement):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    customer = statement.customer
    month = statement.month.month
    year = statement.month.year

    orders = Order.objects.filter(
        customer=customer,
        date__year=year,
        date__month=month
    ).select_related('branch', 'product')

    elements.append(Paragraph(f"Account Statement for {customer.name}", styles['Title']))
    elements.append(Paragraph(f"Month: {statement.month.strftime('%B %Y')}", styles['Normal']))
    elements.append(Paragraph(f"Created On: {statement.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Determine if remarks column is needed
    include_remarks = any(order.remarks for order in orders)

    headers = ['Branch', 'Invoice Code', 'Date', 'Product', 'Boxes', 'Stems/Box', 'Total Stems', 'Price/Stem', 'Amount']
    if include_remarks:
        headers.append('Remarks')

    data = [headers]

    total_amount = 0
    currency = None

    for order in orders:
        amount = order.total_amount
        total_amount += amount
        currency = order.currency  # Assuming all in same currency

        row = [
            order.branch.name if order.branch else "—",
            order.invoice_code,
            order.date.strftime('%Y-%m-%d'),
            order.product.name,
            order.boxes,
            order.stems_per_box,
            order.stems,
            f"{order.price_per_stem:.2f}",
            f"{amount:.2f} {order.currency}"
        ]

        if include_remarks:
            row.append(order.remarks or '')

        data.append(row)

    # Summary row
    summary_row = [''] * 8
    if include_remarks:
        summary_row.append('')  # maintain column alignment

    summary_row[-2] = 'Total:'
    summary_row[-1] = f"{total_amount:.2f} {currency or ''}"
    data.append(summary_row)

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()
