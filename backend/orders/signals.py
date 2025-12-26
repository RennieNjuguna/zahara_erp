from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from invoices.models import Invoice
from invoices.utils import generate_invoice_pdf
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def create_or_update_invoice(sender, instance, created, **kwargs):
    """
    Auto-create or update Invoice when Order is saved.
    Generate PDF for the invoice.
    """
    try:
        # Create invoice if it doesn't exist
        invoice, created_invoice = Invoice.objects.get_or_create(
            order=instance,
            defaults={'invoice_code': instance.invoice_code}
        )
        
        # If invoice code somehow differs (e.g. order code changed), update it
        if invoice.invoice_code != instance.invoice_code:
            invoice.invoice_code = instance.invoice_code
            invoice.save(update_fields=['invoice_code'])

        # Generate PDF
        # We generate PDF on every save to keep it updated with changes
        try:
            generate_invoice_pdf(invoice)
        except Exception as e:
            logger.error(f"Failed to generate PDF for order {instance.invoice_code}: {e}")
            
    except Exception as e:
        logger.error(f"Error handling invoice for order {instance.invoice_code}: {e}")
