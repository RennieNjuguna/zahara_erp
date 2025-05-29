from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from orders.models import Order
from customers.models import Customer, Branch
from datetime import datetime

def generate_account_statement_pdf(statement):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    customer = statement.customer
    month = statement.month.month
    year = statement.month.year

    # Include branches
    branches = Branch.objects.filter(customer=customer)
    customer_ids = [customer.id] + [branch.id for branch in branches]

    orders = Order.objects.filter(
        customer__in=customer_ids,
        date__year=year,
        date__month=month
    ).select_related('customer', 'branch', 'product')

    elements.append(Paragraph(f"Account Statement for {customer.name}", styles['Title']))
    elements.append(Paragraph(f"Month: {statement.month.strftime('%B %Y')}", styles['Normal']))
    elements.append(Paragraph(f"Created On: {statement.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    headers = ['Branch', 'Invoice Code', 'Date', 'Product', 'Boxes', 'Stems/Box', 'Total Stems', 'Price/Stem', 'Amount', 'Final Amount', 'Remarks']
    data = [headers]

    total_amount = 0
    total_final_amount = 0
    currency = customer.preferred_currency

    for order in orders:
        credited_stems = sum(cn.stems_affected for cn in order.credit_notes.all())
        final_amount = (order.stems - credited_stems) * order.price_per_stem
        total_amount += order.total_amount
        total_final_amount += final_amount

        row = [
            order.branch.name if order.branch else "—",
            order.invoice_code,
            order.date.strftime('%Y-%m-%d'),
            order.product.name,
            order.boxes,
            order.stems_per_box,
            order.stems,
            f"{order.price_per_stem:.2f}",
            f"{order.total_amount:.2f} {order.currency}",
            f"{final_amount:.2f} {order.currency}",
            order.remarks or '',
        ]
        data.append(row)

    # Summary row
    summary_row = [''] * 8
    summary_row[-3] = 'Total:'
    summary_row[-2] = f"{total_amount:.2f} {currency}"
    summary_row[-1] = f"{total_final_amount:.2f} {currency}"
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
