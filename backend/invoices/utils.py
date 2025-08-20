import subprocess
import shutil
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
import tempfile
import os
from io import BytesIO
from django.db.models import Q
from reportlab.pdfgen import canvas
from customers.models import Branch
from orders.models import Order
from django.conf import settings

def generate_invoice_pdf(invoice):
    """Generate PDF for an invoice using wkhtmltopdf with ReportLab fallback"""
    from django.template.loader import render_to_string
    from django.conf import settings
    import tempfile
    import os
    import shutil
    import subprocess
    from django.core.files.base import ContentFile

    # Render the HTML template
    context = {
        'invoice': invoice,
        'static_base': f'file:///{os.path.join(settings.BASE_DIR, "static").replace(os.sep, "/")}'
    }
    html_string = render_to_string('invoice_pdf.html', context)

    # Check if wkhtmltopdf is available
    wkhtmltopdf_path = shutil.which('wkhtmltopdf')
    html_file_path = None
    pdf_file_path = None

    try:
        if wkhtmltopdf_path:
            # Use wkhtmltopdf
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as html_file:
                html_file.write(html_string.encode('utf-8'))
                html_file_path = html_file.name

            pdf_file_path = html_file_path.replace('.html', '.pdf')
            subprocess.run([wkhtmltopdf_path, '--enable-local-file-access', html_file_path, pdf_file_path], check=True)

            with open(pdf_file_path, 'rb') as pdf_file:
                invoice.pdf_file.save(f"{invoice.invoice_code}.pdf", ContentFile(pdf_file.read()))
        else:
            # Fallback with ReportLab minimal invoice
            buffer = BytesIO()
            p = canvas.Canvas(buffer)
            p.setFont("Helvetica", 18)
            p.drawString(72, 800, f"Invoice {invoice.invoice_code}")
            p.setFont("Helvetica", 12)
            p.drawString(72, 780, f"Date: {invoice.order.date.strftime('%Y-%m-%d')}")
            p.drawString(72, 765, f"Customer: {invoice.order.customer.name}")
            y = 740
            p.drawString(72, y, "Items:")
            y -= 20
            for item in invoice.order.items.all():
                line = f"- {item.product.name} | {item.stems} stems @ {item.price_per_stem} = {item.total_amount}"
                p.drawString(90, y, line)
                y -= 16
                if y < 100:
                    p.showPage()
                    y = 800
            p.drawString(72, y-10, f"Total: {invoice.order.total_amount} {invoice.order.currency}")
            p.showPage()
            p.save()

            buffer.seek(0)
            invoice.pdf_file.save(f"{invoice.invoice_code}.pdf", ContentFile(buffer.read()))
            buffer.close()
    finally:
        # Cleanup temp files if created
        if html_file_path and os.path.isfile(html_file_path):
            os.remove(html_file_path)
        if pdf_file_path and os.path.isfile(pdf_file_path):
            os.remove(pdf_file_path)

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
        # For each item, sum credited stems from all related CreditNoteItems
        for item in order.items.all():
            credited_stems = sum(
                cni.stems_affected for cni in item.credit_notes.through.objects.filter(order_item=item)
            )
            final_amount = (item.stems - credited_stems) * item.price_per_stem
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
    pdf_bytes = buffer.read()
    statement.pdf_file.save(f"{customer.short_code}_statement_{month.strftime('%Y_%m')}.pdf", ContentFile(pdf_bytes))
    buffer.close()
    return pdf_bytes
