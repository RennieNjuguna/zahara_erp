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

class AccountStatement(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    month = models.DateField(help_text="Set any date in the target month")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    pdf_file = models.FileField(upload_to='account_statements_pdfs/', blank=True, null=True)

    def __str__(self):
        return f"{self.customer.name} - {self.month.strftime('%B %Y')}"

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

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True)  # Check number, transaction ID, etc.
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.amount} {self.customer.preferred_currency} - {self.payment_date}"

    def allocated_amount(self):
        """Return the total amount allocated to orders"""
        return sum(allocation.amount for allocation in self.allocations.all())

    def unallocated_amount(self):
        """Return the amount not yet allocated to orders"""
        return self.amount - self.allocated_amount()

class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.amount > self.payment.unallocated_amount() + self.amount:
            raise ValidationError("Allocation amount exceeds available payment amount")
        if self.amount > self.order.outstanding_amount():
            raise ValidationError("Allocation amount exceeds order outstanding amount")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payment} -> {self.order.invoice_code}: {self.amount}"

# Add outstanding_amount method to Order model
def order_outstanding_amount(self):
    """Calculate outstanding amount for this order"""
    total_credits = sum(
        cni.credit_amount for cni in self.credit_notes.through.objects.filter(order_item__order=self)
    )
    total_payments = sum(
        allocation.amount for allocation in self.payment_allocations.all()
    )
    return self.total_amount - total_credits - total_payments

# Add this method to Order model
Order.outstanding_amount = order_outstanding_amount

# Add outstanding_amount method to Customer model
def customer_outstanding_amount(self):
    """Calculate total outstanding amount for this customer"""
    total_outstanding = 0
    for order in self.orders.all():
        total_outstanding += order.outstanding_amount()
    return total_outstanding

# Add this method to Customer model (we'll need to import Customer)
from customers.models import Customer
Customer.outstanding_amount = customer_outstanding_amount
