from django.db import models
from orders.models import Order, OrderItem
from customers.models import Customer
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_code = models.CharField(max_length=20, unique=True)
    pdf_file = models.FileField(upload_to='invoices_pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.invoice_code


class CreditNote(models.Model):
    """
    Redesigned Credit Note model.
    Linked to a Customer, allowing items from multiple Orders.
    """
    STATUS_CHOICES = [
        ('pending', 'Draft / Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ]

    code = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credit_notes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    currency = models.CharField(max_length=3, choices=Customer.CURRENCY_CHOICES)
    
    reason = models.TextField(help_text="Reason for the credit note")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.currency:
            self.currency = self.customer.preferred_currency
        super().save(*args, **kwargs)

    def calculate_total(self):
        """Recalculate total amount from items and update code based on orders"""
        self.total_amount = sum(item.amount for item in self.items.all())
        
        # Update Code to CN-[OrderCode]
        if self.items.exists():
            # Find earliest order
            orders = sorted(
                list(set(item.order_item.order for item in self.items.all())),
                key=lambda o: o.date
            )
            if orders:
                earliest_order = orders[0]
                new_code = f"CN-{earliest_order.invoice_code}"
                
                # Check uniqueness (handle duplicates if multiple CNs for same order)
                if self.code != new_code:
                    original_new_code = new_code
                    counter = 1
                    while CreditNote.objects.filter(code=new_code).exclude(id=self.id).exists():
                        counter += 1
                        new_code = f"{original_new_code}-{counter}"
                    
                    self.code = new_code
        
        self.save(update_fields=['total_amount', 'code'])

    def approve(self):
        """Approve the credit note and update related orders/balances"""
        if self.status != 'pending':
            raise ValidationError("Only pending credit notes can be approved.")
        
        # 1. Update status
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.save()

        # 2. Update Customer Balance
        from payments.models import CustomerBalance
        balance, _ = CustomerBalance.objects.get_or_create(
            customer=self.customer,
            defaults={'currency': self.currency}
        )
        balance.recalculate_balance()

        # 3. Update Orders Logic
        # Update status of all affected orders to Partial Claim / Full Claim
        affected_orders = set(item.order_item.order for item in self.items.all())
        for order in affected_orders:
            order.update_status_from_credit_note()


class CreditNoteItem(models.Model):
    """
    Individual line item in a Credit Note.
    Links to a specific Order Item.
    """
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='credit_items')
    
    stems = models.PositiveIntegerField(help_text="Number of stems credited")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Credit amount for this line")
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.credit_note.code} - {self.order_item.product.name}"

    def save(self, *args, **kwargs):
        # Auto-calculate amount if not set, based on stems * price
        if self.stems and not self.amount:
            self.amount = self.stems * self.order_item.price_per_stem
        super().save(*args, **kwargs)


@receiver(pre_save, sender=CreditNote)
def generate_credit_note_code(sender, instance, **kwargs):
    if not instance.code:
        # Generate temporary code until items are added
        import uuid
        instance.code = f"TEMP-{uuid.uuid4().hex[:8].upper()}"

@receiver(post_save, sender=CreditNoteItem)
def update_credit_note_total(sender, instance, **kwargs):
    instance.credit_note.calculate_total()

@receiver(models.signals.post_delete, sender=CreditNoteItem)
def update_credit_note_total_on_delete(sender, instance, **kwargs):
    instance.credit_note.calculate_total()
