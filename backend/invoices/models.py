from django.db import models
from orders.models import Order, OrderItem
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



class CreditNoteItem(models.Model):
    credit_note = models.ForeignKey('CreditNote', on_delete=models.CASCADE, related_name='credit_note_items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    stems_affected = models.PositiveIntegerField()
    credit_amount = models.DecimalField(default=1, max_digits=12, decimal_places=2, editable=False)

    def clean(self):
        if self.stems_affected > self.order_item.stems:
            raise ValidationError(f"Stems affected for {self.order_item.product.name} cannot exceed order item stems.")

    def save(self, *args, **kwargs):
        self.credit_amount = self.stems_affected * self.order_item.price_per_stem
        super().save(*args, **kwargs)

class CreditNote(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='credit_notes')
    order_items = models.ManyToManyField(OrderItem, through='CreditNoteItem', related_name='credit_notes')
    title = models.CharField(max_length=100)
    reason = models.TextField()
    created_at = models.DateTimeField(default=datetime.datetime.now)

    def clean(self):
        for cni in self.credit_note_items.all():
            cni.clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for cni in self.credit_note_items.all():
            credited_stems = sum(
                item.stems_affected for item in CreditNoteItem.objects.filter(order_item=cni.order_item).exclude(credit_note=self)
            )
            if credited_stems + cni.stems_affected > cni.order_item.stems:
                raise ValidationError(f"Total credited stems for {cni.order_item.product.name} cannot exceed order item stems.")
            cni.order_item.total_amount = (cni.order_item.stems - credited_stems - cni.stems_affected) * cni.order_item.price_per_stem
            cni.order_item.save()
        # Update order total
        self.order.total_amount = sum(item.total_amount for item in self.order.items.all())
        self.order.save()

    def apply_credit(self):
        for cni in self.credit_note_items.all():
            credited_stems = sum(
                item.stems_affected for item in CreditNoteItem.objects.filter(order_item=cni.order_item).exclude(credit_note=self)
            )
            if credited_stems + cni.stems_affected > cni.order_item.stems:
                raise ValidationError(f"Total credited stems for {cni.order_item.product.name} cannot exceed order item stems.")
            cni.order_item.total_amount = (cni.order_item.stems - credited_stems - cni.stems_affected) * cni.order_item.price_per_stem
            cni.order_item.save()
        # Update order total
        self.order.total_amount = sum(item.total_amount for item in self.order.items.all())
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

# Payment and PaymentAllocation models have been moved to the payments app
# These models are now handled by the new payment system
