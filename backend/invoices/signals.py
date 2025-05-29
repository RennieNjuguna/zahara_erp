from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from .models import Invoice
from .utils import generate_invoice_pdf
import os

@receiver(post_save, sender=Order)
def create_or_update_invoice_for_order(sender, instance, **kwargs):
    invoice, created = Invoice.objects.get_or_create(order=instance, defaults={'invoice_code': instance.invoice_code})

    if not created and invoice.pdf_file and os.path.isfile(invoice.pdf_file.path):
        os.remove(invoice.pdf_file.path)

    generate_invoice_pdf(invoice)
