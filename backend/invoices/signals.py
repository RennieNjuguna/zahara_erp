from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from .models import Invoice
from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
from io import BytesIO
import os

def generate_invoice_pdf(invoice, order):
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
    p.drawString(100, 690, f"Product: {order.product.name}")
    p.drawString(100, 670, f"Boxes: {order.boxes}")
    p.drawString(100, 650, f"Stems per Box: {order.stems_per_box}")
    p.drawString(100, 630, f"Total Stems: {order.stems}")
    p.drawString(100, 590, f"Price per Stem: {order.price_per_stem} {order.currency}")
    p.drawString(100, 610, f"Total Amount: {order.total_amount} {order.currency}")

    p.showPage()
    p.save()

    buffer.seek(0)
    invoice.pdf_file.save(f"{order.invoice_code}.pdf", ContentFile(buffer.read()))
    buffer.close()

@receiver(post_save, sender=Order)
def create_or_update_invoice_for_order(sender, instance, **kwargs):
    invoice, created = Invoice.objects.get_or_create(order=instance, defaults={'invoice_code': instance.invoice_code})

    if not created:
        # If the invoice exists and we’re editing the order, regenerate the PDF
        if invoice.pdf_file:
            if os.path.isfile(invoice.pdf_file.path):
                os.remove(invoice.pdf_file.path)

    generate_invoice_pdf(invoice, instance)
