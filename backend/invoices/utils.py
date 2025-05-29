from reportlab.pdfgen import canvas
from io import BytesIO
from django.core.files.base import ContentFile
from orders.models import Order
from customers.models import Customer, Branch
from .models import Invoice, AccountStatement
from django.db.models import Q

def generate_invoice_pdf(invoice):
    order = invoice.order
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 20)
    p.drawString(100, 800, "Zahara Flowers Invoice")

    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Date: {order.date}")
    p.drawString(100, 750, f"Invoice Code: {order.invoice_code}")
    p.drawString(100, 730, f"Customer: {order.customer.name}")
    if order.branch:
        p.drawString(100, 710, f"Branch: {order.branch.name}")
    y = 690
    for item in order.items.all():
        p.drawString(100, y, f"Product: {item.product.name}")
        p.drawString(100, y-20, f"Boxes: {item.boxes}")
        p.drawString(100, y-40, f"Stems per Box: {item.stems_per_box}")
        p.drawString(100, y-60, f"Total Stems: {item.stems}")
        p.drawString(100, y-80, f"Price per Stem: {item.price_per_stem} {order.currency}")
        p.drawString(100, y-100, f"Item Total: {item.total_amount} {order.currency}")
        y -= 120
    p.drawString(100, y-20, f"Total Amount: {order.total_amount} {order.currency}")
    if order.remarks:
        p.drawString(100, y-40, f"Remarks: {order.remarks}")

    p.showPage()
    p.save()

    buffer.seek(0)
    invoice.pdf_file.save(f"{order.invoice_code}.pdf", ContentFile(buffer.read()))
    buffer.close()

def generate_account_statement_pdf(statement):
    customer = statement.customer
    month = statement.month

    branches = Branch.objects.filter(customer=customer)
    branch_ids = branches.values_list('id', flat=True)

    orders = Order.objects.filter(
        Q(customer=customer) | Q(branch__in=branch_ids),
        date__year=month.year,
        date__month=month.month
    ).order_by('date')

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 20)
    p.drawString(100, 800, f"Account Statement for {customer.name}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Month: {month.strftime('%B %Y')}")

    y = 760
    p.drawString(100, y, "Invoice Code")
    p.drawString(200, y, "Date")
    p.drawString(300, y, "Product")
    p.drawString(400, y, "Total Stems")
    p.drawString(500, y, "Final Amount")
    p.drawString(600, y, "Remarks")
    y -= 20

    total_amount = 0
    for order in orders:
        credited_stems = sum(cn.stems_affected for cn in order.credit_notes.all())
        for item in order.items.all():
            final_amount = (item.stems - credited_stems if item == order.items.first() else item.stems) * item.price_per_stem
            p.drawString(100, y, order.invoice_code)
            p.drawString(200, y, order.date.strftime('%Y-%m-%d'))
            p.drawString(300, y, item.product.name)
            p.drawString(400, y, str(item.stems))
            p.drawString(500, y, f"{final_amount:.2f} {order.currency}")
            p.drawString(600, y, order.remarks or '')
            total_amount += final_amount
            y -= 20

    p.drawString(100, y-20, f"Total: {total_amount:.2f} {customer.preferred_currency}")

    p.showPage()
    p.save()

    buffer.seek(0)
    statement.pdf_file.save(f"{customer.short_code}_statement_{month.strftime('%Y_%m')}.pdf", ContentFile(buffer.read()))
    buffer.close()
