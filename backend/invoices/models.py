from django.db import models
from orders.models import Order
from customers.models import Customer
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import date
import datetime


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_code = models.CharField(max_length=20, unique=True)
    pdf_file = models.FileField(upload_to='invoices_pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.invoice_code

class AccountStatement(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    month = models.DateField(help_text="Set any date in the target month")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"{self.customer.name} - {self.month.strftime('%B %Y')}"


class CreditNote(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='credit_notes')
    title = models.CharField(max_length=100)
    reason = models.TextField()
    stems_affected = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=datetime.date.today)

    def __str__(self):
        return self.code

    def apply_credit(self):
        if self.stems_affected <= self.order.stems:
            self.order.stems -= self.stems_affected
            self.order.total_amount = self.order.stems * self.order.price_per_stem
            self.order.remarks = f"Credit Note issued - {self.code}"
            self.order.save()

@receiver(pre_save, sender=CreditNote)
def generate_credit_note_code(sender, instance, **kwargs):
    if not instance.code:
        last = CreditNote.objects.order_by('id').last()
        next_number = 1 if not last else int(last.code.split('-')[1]) + 1
        instance.code = f'CN-{next_number:03}'

@receiver(post_save, sender=CreditNote)
def apply_credit_after_save(sender, instance, created, **kwargs):
    if created:
        instance.apply_credit()
