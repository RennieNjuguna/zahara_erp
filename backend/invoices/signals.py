from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from .models import Invoice
from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
from io import BytesIO

@receiver(post_save, sender=Order)
def create_invoice_for_order(sender, instance, created, **kwargs):
    if created:
        # Create the Invoice Code
        invoice_code = instance.invoice_code

        # Create Invoice object
        invoice = Invoice.objects.create(order=instance, invoice_code=invoice_code)

        # Now generate a simple PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica", 20)
        p.drawString(100, 800, "Zahara Flowers Invoice")

        p.setFont("Helvetica", 12)
        p.drawString(100, 760, f"Invoice Code: {invoice_code}")
        p.drawString(100, 740, f"Customer: {instance.customer.name}")
        if instance.branch:
            p.drawString(100, 720, f"Branch: {instance.branch.name}")
        p.drawString(100, 700, f"Product: {instance.product.name}")
        p.drawString(100, 680, f"Stems: {instance.stems}")
        p.drawString(100, 660, f"Total Amount: {instance.total_amount} {instance.customer.preferred_currency}")

        p.showPage()
        p.save()

        buffer.seek(0)
        invoice.pdf_file.save(f"{invoice_code}.pdf", ContentFile(buffer.read()))
        buffer.close()
