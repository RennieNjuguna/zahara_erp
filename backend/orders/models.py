from django.db import models
from django.utils import timezone
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal

class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    boxes = models.PositiveIntegerField(default=1)
    stems_per_box = models.PositiveIntegerField(default=1)
    stems = models.PositiveIntegerField(editable=False)
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        # Calculate total stems
        self.stems = self.boxes * self.stems_per_box
        # Fetch price from CustomerProductPrice
        try:
            cpp = CustomerProductPrice.objects.get(customer=self.order.customer, product=self.product)
            self.price_per_stem = cpp.price_per_stem
        except CustomerProductPrice.DoesNotExist:
            raise ValidationError("No price found for this customer and product combination")
        # Calculate total amount for this item
        self.total_amount = self.stems * self.price_per_stem
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} in {self.order.invoice_code}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('claim', 'Claim (Bad Produce)'),
        ('cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    currency = models.CharField(max_length=10, editable=False)
    invoice_code = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField(default=timezone.now)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_reason = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Ensure currency consistency across items
        if self.items.exists():
            currencies = set(item.order.currency for item in self.items.all())
            if len(currencies) > 1:
                raise ValidationError("All items in an order must use the same currency.")
        # Calculate total amount from all items
        self.total_amount = sum(item.total_amount for item in self.items.all())
        # Set currency from customer
        self.currency = self.customer.preferred_currency
        # Generate invoice code if not already set
        if not self.invoice_code:
            short_code = self.branch.short_code if self.branch else self.customer.short_code
            existing_orders = Order.objects.filter(
                invoice_code__startswith=short_code
            ).count() + 1
            self.invoice_code = f"{short_code}{str(existing_orders).zfill(3)}"

        # Update status based on payment allocations if status is pending
        if self.status == 'pending' and self.pk:
            if self.is_paid():
                self.status = 'paid'

        super().save(*args, **kwargs)

    def is_paid(self):
        """Check if the order is fully paid"""
        if self.total_amount == 0:
            return True

        # Get total payments allocated to this order
        total_payments = self.new_payment_allocations.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Get total credits for this order
        from invoices.models import CreditNote
        total_credits = CreditNote.objects.filter(
            order=self
        ).aggregate(
            total=Sum('credit_note_items__credit_amount')
        )['total'] or Decimal('0.00')

        # Order is paid if payments + credits >= total amount
        return (total_payments + total_credits) >= self.total_amount

    def mark_as_claim(self, reason="Bad Produce"):
        """Mark order as claim and create credit note"""
        if self.status != 'pending':
            raise ValidationError("Only pending orders can be marked as claim")

        # Create credit note for the entire order
        from invoices.models import CreditNote, CreditNoteItem

        credit_note = CreditNote.objects.create(
            order=self,
            title=f"Credit Note for {self.invoice_code}",
            reason=reason
        )

        # Create credit note items for all order items
        for item in self.items.all():
            CreditNoteItem.objects.create(
                credit_note=credit_note,
                order_item=item,
                stems_affected=item.stems
            )

        # Update order status
        self.status = 'claim'
        self.status_reason = reason
        self.save()

        return credit_note

    def cancel_order(self, reason="Order Cancelled"):
        """Cancel an order"""
        if self.status not in ['pending', 'paid']:
            raise ValidationError("Only pending or paid orders can be cancelled")

        # Update order status
        self.status = 'cancelled'
        self.status_reason = reason
        self.save()

        return self

    def __str__(self):
        return f"{self.invoice_code} - {self.customer.name}"

    def clean(self):
        if self.branch and self.branch.customer != self.customer:
            raise ValidationError("Selected branch does not belong to the selected customer.")
