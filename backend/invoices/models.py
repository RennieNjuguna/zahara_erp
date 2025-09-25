from django.db import models
from orders.models import Order, OrderItem
from customers.models import Customer
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
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
    """Enhanced Credit Note model with comprehensive order integration"""

    # Basic Information
    code = models.CharField(max_length=20, unique=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='credit_notes')
    title = models.CharField(max_length=100)
    reason = models.TextField(help_text="Reason/issue for the credit note (e.g., damaged items, quality issues, short delivery)")

    # Credit Details
    total_credit_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=0)
    currency = models.CharField(max_length=3, choices=Customer.CURRENCY_CHOICES, editable=False, default='KSH')

    # Status and Processing
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Credit Application Logic
    CREDIT_TYPE_CHOICES = [
        ('order_reduction', 'Order Total Reduction'),
        ('customer_credit', 'Customer Credit Balance'),
    ]
    credit_type = models.CharField(max_length=20, choices=CREDIT_TYPE_CHOICES, default='order_reduction')

    # Audit Information
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_credit_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['currency']),
        ]

    def __str__(self):
        return f"{self.code} - {self.order.invoice_code}"

    def clean(self):
        """Validate credit note before saving"""
        if not self.order:
            raise ValidationError("Credit note must be linked to an order.")

        # Ensure currency matches order currency
        if self.order and self.order.currency:
            self.currency = self.order.currency

        # Validate credit type based on order status
        if self.order and self.order.status == 'paid':
            if self.credit_type == 'order_reduction':
                raise ValidationError("Cannot reduce order total for paid orders. Use customer credit instead.")
        elif self.order and self.order.status == 'pending':
            if self.credit_type == 'customer_credit':
                raise ValidationError("Pending orders should use order reduction. Use customer credit for paid orders.")

    def save(self, *args, **kwargs):
        """Save credit note with automatic processing"""
        self.clean()

        # Set currency from order
        if self.order:
            self.currency = self.order.currency

        # Calculate total credit amount
        self.total_credit_amount = sum(
            item.credit_amount for item in self.credit_note_items.all()
        )

        super().save(*args, **kwargs)

        # Apply credit based on type and order status
        if self.status == 'pending':
            self._apply_credit_logic()

    def _apply_credit_logic(self):
        """Apply credit based on order status and credit type"""
        if self.order.status == 'pending':
            # For pending orders, reduce order total directly
            self.credit_type = 'order_reduction'
            self._reduce_order_total()
        elif self.order.status == 'paid':
            # For paid orders, create customer credit balance
            self.credit_type = 'customer_credit'
            self._create_customer_credit()

        self.status = 'applied'
        self.applied_at = timezone.now()
        self.save(update_fields=['status', 'applied_at'])

    def _reduce_order_total(self):
        """Reduce order total for pending orders"""
        # Update order item totals
        for credit_item in self.credit_note_items.all():
            order_item = credit_item.order_item
            # Calculate remaining stems after credit
            remaining_stems = order_item.stems - credit_item.stems_affected
            if remaining_stems < 0:
                raise ValidationError(f"Cannot credit more stems than ordered for {order_item.product.name}")

            # Update order item total
            order_item.total_amount = remaining_stems * order_item.price_per_stem
            order_item.save()

        # Recalculate order total
        self.order.save()  # This will trigger order total recalculation

    def _create_customer_credit(self):
        """Create customer credit balance for paid orders"""
        from payments.models import CustomerBalance

        # Get or create customer balance
        balance, created = CustomerBalance.objects.get_or_create(
            customer=self.order.customer,
            defaults={'currency': self.currency}
        )

        # Add credit to customer balance
        balance.current_balance -= self.total_credit_amount
        balance.save()

    def get_credit_summary(self):
        """Get summary of credit note items"""
        items = []
        for credit_item in self.credit_note_items.all():
            items.append({
                'product': credit_item.order_item.product.name,
                'stems_affected': credit_item.stems_affected,
                'price_per_stem': credit_item.order_item.price_per_stem,
                'credit_amount': credit_item.credit_amount,
            })
        return items

    def can_be_cancelled(self):
        """Check if credit note can be cancelled"""
        return self.status == 'pending'

    def cancel_credit(self):
        """Cancel the credit note"""
        if not self.can_be_cancelled():
            raise ValidationError("Only pending credit notes can be cancelled")

        self.status = 'cancelled'
        self.save()


class CreditNoteItem(models.Model):
    """Individual items within a credit note for partial credits"""
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name='credit_note_items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='credit_note_items')
    stems_affected = models.PositiveIntegerField(help_text="Number of stems to credit")
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    # Additional tracking
    reason = models.CharField(max_length=255, blank=True, help_text="Specific reason for this item credit")

    class Meta:
        unique_together = ('credit_note', 'order_item')
        indexes = [
            models.Index(fields=['credit_note', 'order_item']),
        ]

    def __str__(self):
        return f"{self.credit_note.code} - {self.order_item.product.name}: {self.stems_affected} stems"

    def clean(self):
        """Validate credit note item"""
        if self.order_item and self.stems_affected:
            # Check if stems affected exceeds order item stems
            if self.stems_affected > self.order_item.stems:
                raise ValidationError(
                    f"Stems affected ({self.stems_affected}) cannot exceed order item stems ({self.order_item.stems})"
                )

            # Check if total credited stems (including this) exceeds order item stems
            total_credited = CreditNoteItem.objects.filter(
                order_item=self.order_item
            ).exclude(credit_note=self.credit_note).aggregate(
                total=models.Sum('stems_affected')
            )['total'] or 0

            if total_credited + self.stems_affected > self.order_item.stems:
                raise ValidationError(
                    f"Total credited stems ({total_credited + self.stems_affected}) cannot exceed order item stems ({self.order_item.stems})"
                )

    def save(self, *args, **kwargs):
        """Save credit note item with automatic calculations"""
        self.clean()

        # Calculate credit amount
        if self.order_item and self.stems_affected:
            self.credit_amount = self.stems_affected * self.order_item.price_per_stem

        super().save(*args, **kwargs)


# Signals for automatic processing
@receiver(pre_save, sender=CreditNote)
def generate_credit_note_code(sender, instance, **kwargs):
    """Generate unique credit note code"""
    if not instance.code:
        # Get the last credit note and increment
        last_credit_note = CreditNote.objects.order_by('-id').first()
        if last_credit_note:
            try:
                last_number = int(last_credit_note.code.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1

        instance.code = f'CN-{next_number:04d}'

@receiver(post_save, sender=CreditNote)
def update_customer_balance_on_credit_note(sender, instance, created, **kwargs):
    """Update customer balance when credit note is created or updated"""
    if created and instance.status == 'applied':
        from payments.models import CustomerBalance

        balance, created = CustomerBalance.objects.get_or_create(
            customer=instance.order.customer,
            defaults={'currency': instance.currency}
        )
        balance.recalculate_balance()

@receiver(post_save, sender=CreditNoteItem)
def update_credit_note_total(sender, instance, created, **kwargs):
    """Update credit note total when items are added/modified"""
    if instance.credit_note:
        instance.credit_note.total_credit_amount = sum(
            item.credit_amount for item in instance.credit_note.credit_note_items.all()
        )
        instance.credit_note.save(update_fields=['total_credit_amount'])

# Payment and PaymentAllocation models have been moved to the payments app
# These models are now handled by the new payment system
