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
    stem_length_cm = models.PositiveIntegerField(help_text="Stem length in centimeters")
    boxes = models.PositiveIntegerField(default=1)
    stems_per_box = models.PositiveIntegerField(default=1)
    stems = models.PositiveIntegerField(editable=False)
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per stem (auto-filled from customer pricing if available)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        # Calculate total stems
        self.stems = self.boxes * self.stems_per_box

        # If price_per_stem is not set, try to fetch from CustomerProductPrice
        if not self.price_per_stem:
            try:
                cpp = CustomerProductPrice.objects.get(
                    customer=self.order.customer,
                    product=self.product,
                    stem_length_cm=self.stem_length_cm
                )
                self.price_per_stem = cpp.price_per_stem
            except CustomerProductPrice.DoesNotExist:
                # If no price found, set price to 0 and allow manual entry
                self.price_per_stem = Decimal('0.00')

        # Calculate total amount for this item
        self.calculate_total_amount()

        # Remember this stem length and price for future orders (only if price > 0)
        if self.price_per_stem > 0:
            self._remember_defaults()
            # Also update CustomerProductPrice to keep it in sync
            self._sync_customer_pricing()

        super().save(*args, **kwargs)

    def _sync_customer_pricing(self):
        """Sync the order item price back to CustomerProductPrice"""
        from products.models import CustomerProductPrice

        if self.price_per_stem > 0:
            # Create or update CustomerProductPrice
            cpp, created = CustomerProductPrice.objects.get_or_create(
                customer=self.order.customer,
                product=self.product,
                stem_length_cm=self.stem_length_cm,
                defaults={'price_per_stem': self.price_per_stem}
            )

            if not created and cpp.price_per_stem != self.price_per_stem:
                # Update existing price
                cpp.price_per_stem = self.price_per_stem
                cpp.save()

    def calculate_total_amount(self):
        """Calculate and update the total amount for this item"""
        self.total_amount = self.stems * self.price_per_stem
        return self.total_amount

    def _remember_defaults(self):
        """Remember stem length and price as defaults for future orders"""
        from .models import CustomerOrderDefaults

        # Only remember defaults if we have a valid price
        if self.price_per_stem <= 0:
            return

        defaults, created = CustomerOrderDefaults.objects.get_or_create(
            customer=self.order.customer,
            product=self.product,
            defaults={
                'stem_length_cm': self.stem_length_cm,
                'price_per_stem': self.price_per_stem
            }
        )

        if not created:
            # Update existing defaults
            defaults.stem_length_cm = self.stem_length_cm
            defaults.price_per_stem = self.price_per_stem
            defaults.save()

    def update_price_from_customer_pricing(self):
        """Update price from CustomerProductPrice if available"""
        try:
            cpp = CustomerProductPrice.objects.get(
                customer=self.order.customer,
                product=self.product,
                stem_length_cm=self.stem_length_cm
            )
            if cpp.price_per_stem != self.price_per_stem:
                self.price_per_stem = cpp.price_per_stem
                self.total_amount = self.stems * self.price_per_stem
                self.save()
                return True
        except CustomerProductPrice.DoesNotExist:
            pass
        return False

    def update_price(self, new_price):
        """Update price and sync to CustomerProductPrice"""
        if new_price != self.price_per_stem:
            self.price_per_stem = new_price
            self.calculate_total_amount()
            self.save()
            # Sync to CustomerProductPrice
            if self.price_per_stem > 0:
                self._sync_customer_pricing()
            return True
        return False

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

    # Logistics fields
    logistics_provider = models.CharField(max_length=100, blank=True, null=True, help_text="Logistics provider name")
    logistics_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Cost of logistics/shipping")
    tracking_number = models.CharField(max_length=100, blank=True, null=True, help_text="Tracking number for the shipment")
    delivery_status = models.CharField(max_length=50, blank=True, null=True, help_text="Delivery status (e.g., In Transit, Delivered, etc.)")

    def save(self, *args, **kwargs):
        # Ensure currency consistency across items
        if self.items.exists():
            currencies = set(item.order.currency for item in self.items.all())
            if len(currencies) > 1:
                raise ValidationError("All items in an order must use the same currency.")
        # Calculate total amount from all items and add logistics cost if present
        items_total = sum(item.total_amount for item in self.items.all())
        if self.logistics_cost:
            self.total_amount = items_total + self.logistics_cost
        else:
            self.total_amount = items_total
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

    def outstanding_amount(self):
        """Calculate outstanding amount for this order"""
        # Get total credits for this order
        from invoices.models import CreditNote
        total_credits = CreditNote.objects.filter(
            order=self
        ).aggregate(
            total=Sum('credit_note_items__credit_amount')
        )['total'] or Decimal('0.00')

        # Outstanding amount is total amount minus payments and credits
        total_payments = self.new_payment_allocations.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        return self.total_amount - total_payments - total_credits

    def subtotal_amount(self):
        """Calculate subtotal amount (items only, excluding logistics)"""
        return sum(item.total_amount for item in self.items.all())

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

    def update_prices_from_customer_pricing(self):
        """Update all order item prices from CustomerProductPrice and recalculate totals"""
        updated = False
        for item in self.items.all():
            if item.update_price_from_customer_pricing():
                updated = True

        if updated:
            # Recalculate order total
            self.total_amount = sum(item.total_amount for item in self.items.all())
            self.save()

        return updated

    def sync_prices_to_customer_pricing(self):
        """Sync all order item prices to CustomerProductPrice"""
        synced_count = 0
        for item in self.items.all():
            if item.price_per_stem > 0:
                item._sync_customer_pricing()
                synced_count += 1
        return synced_count



# Django signals for automatic price syncing
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=OrderItem)
def sync_order_item_price_to_customer_pricing(sender, instance, created, **kwargs):
    """Automatically sync OrderItem price to CustomerProductPrice when saved"""
    if instance.price_per_stem > 0:
        instance._sync_customer_pricing()

class CustomerOrderDefaults(models.Model):
    """Remember stem length and price defaults for each customer-product combination"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='order_defaults')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='customer_defaults')
    stem_length_cm = models.PositiveIntegerField(help_text="Default stem length in centimeters")
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2, help_text="Default price per stem")
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'product')
        verbose_name_plural = "Customer order defaults"

    def __str__(self):
        return f"{self.customer.name} - {self.product.name}: {self.stem_length_cm}cm @ {self.price_per_stem}"

    @classmethod
    def get_defaults(cls, customer, product):
        """Get default stem length and price for a customer-product combination"""
        try:
            defaults = cls.objects.get(customer=customer, product=product)
            return {
                'stem_length_cm': defaults.stem_length_cm,
                'price_per_stem': defaults.price_per_stem
            }
        except cls.DoesNotExist:
            return None
