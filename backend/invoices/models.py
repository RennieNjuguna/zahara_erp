from django.db import models
from orders.models import Order
from customers.models import Customer
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
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
    credit_amount = models.DecimalField(default=1, max_digits=12, decimal_places=2, editable=False)
    created_at = models.DateTimeField(default=datetime.datetime.now)

    def clean(self):
        if self.stems_affected > self.order.stems:
            raise ValidationError("Stems affected cannot exceed order stems.")

    def save(self, *args, **kwargs):
        # Calculate credit amount
        self.credit_amount = self.stems_affected * self.order.price_per_stem
        super().save(*args, **kwargs)

    def apply_credit(self):
        # Update order total_amount and remarks without changing stems
        credited_stems = sum(cn.stems_affected for cn in self.order.credit_notes.all())
        if credited_stems > self.order.stems:
            raise ValidationError("Total credited stems cannot exceed order stems.")
        self.order.total_amount = (self.order.stems - credited_stems) * self.order.price_per_stem
        self.order.remarks = f"Credit Note {self.code}: {self.stems_affected} stems credited, {self.credit_amount:.2f} {self.order.currency} deducted"
        self.order.save()

    def __str__(self):
        return self.code

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
