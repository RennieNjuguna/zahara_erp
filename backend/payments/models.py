from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from customers.models import Customer
from orders.models import Order
from invoices.models import CreditNote
import uuid
from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class PaymentType(models.Model):
    """Payment type configuration for different payment modes"""
    PAYMENT_MODE_CHOICES = [
        ('per_order', 'Per Order Payment'),
        ('bulk', 'Bulk Payment'),
        ('monthly', 'Monthly Payment'),
    ]

    name = models.CharField(max_length=100)
    mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_mode_display()})"


class Payment(models.Model):
    """Main payment record with flexible allocation capabilities"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('mobile_money', 'Mobile Money'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    # Basic payment information
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='new_payments')
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT)

    # Payment details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Customer.CURRENCY_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    # Reference and notes
    reference_number = models.CharField(max_length=100, blank=True, help_text="Check number, transaction ID, etc.")
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'payment_date']),
            models.Index(fields=['status', 'payment_date']),
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.amount} {self.currency} - {self.payment_date}"

    def clean(self):
        if not self.currency:
            self.currency = self.customer.preferred_currency

        if self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def allocated_amount(self):
        """Total amount allocated to orders"""
        amount = self.allocations.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        return Decimal(str(amount)).quantize(Decimal('0.01'))

    @property
    def unallocated_amount(self):
        """Amount not yet allocated to orders"""
        if self.amount is None:
            return Decimal('0.00')
        unallocated = self.amount - self.allocated_amount
        return Decimal(str(unallocated)).quantize(Decimal('0.01'))

    @property
    def is_fully_allocated(self):
        """Check if payment is fully allocated"""
        return self.unallocated_amount == 0

    def allocate_to_orders(self, allocations_data):
        """
        Allocate payment to specific orders
        allocations_data: list of dicts with 'order_id' and 'amount' keys
        """
        total_allocation = sum(item['amount'] for item in allocations_data)

        if total_allocation > self.unallocated_amount:
            raise ValidationError("Total allocation amount exceeds unallocated payment amount")

        allocations = []
        for item in allocations_data:
            order = Order.objects.get(id=item['order_id'])
            allocation = PaymentAllocation.objects.create(
                payment=self,
                order=order,
                amount=item['amount']
            )
            allocations.append(allocation)

        return allocations


class PaymentAllocation(models.Model):
    """Links payments to specific orders with allocated amounts"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='new_payment_allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['payment', 'order']),
        ]

    def __str__(self):
        return f"{self.payment} -> {self.order.invoice_code}: {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Allocation amount must be greater than zero.")

        # Check if allocation exceeds payment unallocated amount
        if self.pk is None:  # New allocation
            if self.amount > self.payment.unallocated_amount:
                raise ValidationError("Allocation amount exceeds available payment amount")

        # Check if allocation exceeds order outstanding amount
        if self.amount > self.order.outstanding_amount():
            raise ValidationError("Allocation amount exceeds order outstanding amount")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class CustomerBalance(models.Model):
    """Real-time customer balance tracking"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='balance')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, choices=Customer.CURRENCY_CHOICES)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name}: {self.current_balance} {self.currency}"

    def recalculate_balance(self):
        """Recalculate customer balance from orders and payments"""
        # Get all orders for customer
        total_orders = Order.objects.filter(customer=self.customer).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # Get all credit notes for customer
        total_credits = CreditNote.objects.filter(
            customer=self.customer
        ).aggregate(
            total=Sum('items__amount')
        )['total'] or Decimal('0.00')

        # Get all payments for customer
        total_payments = Payment.objects.filter(
            customer=self.customer,
            status='completed'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Calculate balance and round to 2 decimal places
        self.current_balance = Decimal(str(total_orders - total_credits - total_payments)).quantize(Decimal('0.01'))
        self.currency = self.customer.preferred_currency
        self.save()

        return self.current_balance


class AccountStatement(models.Model):
    """Dynamic account statements for customers"""

    # Statement Types
    STATEMENT_TYPE_CHOICES = [
        ('reconciliation', 'Reconciliation Statement'),
        ('periodic', 'Periodic Statement'),
        ('full_history', 'Full Account History'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='account_statements')
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPE_CHOICES, default='reconciliation')
    statement_date = models.DateField()
    start_date = models.DateField()
    end_date = models.DateField()

    # Custom Statement Options
    include_payments = models.BooleanField(default=True, help_text="Include payments in the statement")
    include_credits = models.BooleanField(default=True, help_text="Include credit notes in the statement")

    # Statement totals
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_orders = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credits = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payments = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Additional totals for custom statements
    total_pending_orders = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_paid_orders = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_partial_orders = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_claim_orders = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # PDF file
    pdf_file = models.FileField(upload_to='account_statements_pdfs/', blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=100, blank=True)

    class Meta:
        # Allow multiple statements per customer per date for maximum flexibility
        # unique_together = ['customer', 'statement_date', 'statement_type']  # Removed for flexibility
        ordering = ['-statement_date']

    def __str__(self):
        return f"{self.customer.name} - {self.statement_date.strftime('%B %Y')}"

    def generate_statement_data(self):
        """Generate statement data based on statement type and options"""

        if self.statement_type == 'reconciliation':
            return self._generate_reconciliation_statement()
        elif self.statement_type == 'periodic':
            return self._generate_periodic_statement()
        elif self.statement_type == 'full_history':
            return self._generate_full_history_statement()
        else:
            raise ValueError(f"Unknown statement type: {self.statement_type}")

    def _generate_reconciliation_statement(self):
        """Generate full reconciliation statement (existing logic)"""
        # Get opening balance (balance before start_date)
        opening_balance = self._calculate_balance_before_date(self.start_date)

        # Get orders in period
        orders_in_period = Order.objects.filter(
            customer=self.customer,
            date__gte=self.start_date,
            date__lte=self.end_date
        )
        total_orders = orders_in_period.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # Get credits in period
        credits_in_period = CreditNote.objects.filter(
            customer=self.customer,
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date
        )
        total_credits = credits_in_period.aggregate(
            total=Sum('items__amount')
        )['total'] or Decimal('0.00')

        # Get payments in period - include all active payments (completed, pending, but not cancelled/refunded)
        payments_in_period = Payment.objects.filter(
            customer=self.customer,
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        ).exclude(status__in=['cancelled', 'refunded'])

        total_payments = payments_in_period.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Calculate closing balance
        closing_balance = opening_balance + total_orders - total_credits - total_payments

        # Update statement with proper rounding to 2 decimal places
        self.opening_balance = Decimal(str(opening_balance)).quantize(Decimal('0.01'))
        self.closing_balance = Decimal(str(closing_balance)).quantize(Decimal('0.01'))
        self.total_orders = Decimal(str(total_orders)).quantize(Decimal('0.01'))
        self.total_credits = Decimal(str(total_credits)).quantize(Decimal('0.01'))
        self.total_payments = Decimal(str(total_payments)).quantize(Decimal('0.01'))
        self.save()

        return {
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_orders': total_orders,
            'total_credits': total_credits,
            'total_payments': total_payments,
            'orders': orders_in_period,
            'credits': credits_in_period,
            'payments': payments_in_period,
        }

    def _generate_periodic_statement(self):
        """Generate periodic statement with optional payments/credits"""
        # Get orders in period with status breakdown
        orders_in_period = Order.objects.filter(
            customer=self.customer,
            date__gte=self.start_date,
            date__lte=self.end_date
        )

        # Calculate totals by status
        total_orders = orders_in_period.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_pending_orders = orders_in_period.filter(status='pending').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_paid_orders = orders_in_period.filter(status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_partial_orders = orders_in_period.filter(status='partial').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_claim_orders = orders_in_period.filter(status='claim').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # Initialize totals
        total_credits = Decimal('0.00')
        total_payments = Decimal('0.00')
        credits_in_period = None
        payments_in_period = None

        # Include credits if requested
        if self.include_credits:
            credits_in_period = CreditNote.objects.filter(
                customer=self.customer,
                created_at__date__gte=self.start_date,
                created_at__date__lte=self.end_date
            )
            total_credits = credits_in_period.aggregate(
                total=Sum('items__amount')
            )['total'] or Decimal('0.00')

        # Include payments if requested
        if self.include_payments:
            payments_in_period = Payment.objects.filter(
                customer=self.customer,
                payment_date__gte=self.start_date,
                payment_date__lte=self.end_date
            ).exclude(status__in=['cancelled', 'refunded'])
            total_payments = payments_in_period.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

        # Calculate balances
        opening_balance = self._calculate_balance_before_date(self.start_date)
        closing_balance = opening_balance + total_orders - total_credits - total_payments

        # Update statement with proper rounding
        self.opening_balance = Decimal(str(opening_balance)).quantize(Decimal('0.01'))
        self.closing_balance = Decimal(str(closing_balance)).quantize(Decimal('0.01'))
        self.total_orders = Decimal(str(total_orders)).quantize(Decimal('0.01'))
        self.total_credits = Decimal(str(total_credits)).quantize(Decimal('0.01'))
        self.total_payments = Decimal(str(total_payments)).quantize(Decimal('0.01'))
        self.total_pending_orders = Decimal(str(total_pending_orders)).quantize(Decimal('0.01'))
        self.total_paid_orders = Decimal(str(total_paid_orders)).quantize(Decimal('0.01'))
        self.total_partial_orders = Decimal(str(total_partial_orders)).quantize(Decimal('0.01'))
        self.total_claim_orders = Decimal(str(total_claim_orders)).quantize(Decimal('0.01'))
        self.save()

        return {
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_orders': total_orders,
            'total_credits': total_credits,
            'total_payments': total_payments,
            'total_pending_orders': total_pending_orders,
            'total_paid_orders': total_paid_orders,
            'total_partial_orders': total_partial_orders,
            'total_claim_orders': total_claim_orders,
            'orders': orders_in_period,
            'credits': credits_in_period,
            'payments': payments_in_period,
        }

    def _generate_full_history_statement(self):
        """Generate full account history statement"""
        # Get customer's first order date
        first_order = Order.objects.filter(customer=self.customer).order_by('date').first()
        if first_order:
            start_date = first_order.date
        else:
            start_date = self.start_date

        # Get all orders since first order
        all_orders = Order.objects.filter(
            customer=self.customer,
            date__gte=start_date,
            date__lte=self.end_date
        )

        # Calculate totals by status
        total_orders = all_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_pending_orders = all_orders.filter(status='pending').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_paid_orders = all_orders.filter(status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_partial_orders = all_orders.filter(status='partial').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_claim_orders = all_orders.filter(status='claim').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # Initialize totals
        total_credits = Decimal('0.00')
        total_payments = Decimal('0.00')
        credits_in_period = None
        payments_in_period = None

        # Include credits if requested
        if self.include_credits:
            credits_in_period = CreditNote.objects.filter(
                customer=self.customer,
                created_at__date__gte=start_date,
                created_at__date__lte=self.end_date
            )
            total_credits = credits_in_period.aggregate(
                total=Sum('items__amount')
            )['total'] or Decimal('0.00')

        # Include payments if requested
        if self.include_payments:
            payments_in_period = Payment.objects.filter(
                customer=self.customer,
                payment_date__gte=start_date,
                payment_date__lte=self.end_date
            ).exclude(status__in=['cancelled', 'refunded'])
            total_payments = payments_in_period.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

        # Calculate balances
        opening_balance = Decimal('0.00')  # Starting from zero for full history
        closing_balance = opening_balance + total_orders - total_credits - total_payments

        # Update statement with proper rounding
        self.opening_balance = Decimal(str(opening_balance)).quantize(Decimal('0.01'))
        self.closing_balance = Decimal(str(closing_balance)).quantize(Decimal('0.01'))
        self.total_orders = Decimal(str(total_orders)).quantize(Decimal('0.01'))
        self.total_credits = Decimal(str(total_credits)).quantize(Decimal('0.01'))
        self.total_payments = Decimal(str(total_payments)).quantize(Decimal('0.01'))
        self.total_pending_orders = Decimal(str(total_pending_orders)).quantize(Decimal('0.01'))
        self.total_paid_orders = Decimal(str(total_paid_orders)).quantize(Decimal('0.01'))
        self.total_partial_orders = Decimal(str(total_partial_orders)).quantize(Decimal('0.01'))
        self.total_claim_orders = Decimal(str(total_claim_orders)).quantize(Decimal('0.01'))
        self.save()

        return {
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_orders': total_orders,
            'total_credits': total_credits,
            'total_payments': total_payments,
            'total_pending_orders': total_pending_orders,
            'total_paid_orders': total_paid_orders,
            'total_partial_orders': total_partial_orders,
            'total_claim_orders': total_claim_orders,
            'orders': all_orders,
            'credits': credits_in_period,
            'payments': payments_in_period,
        }

    def recalculate_statement(self):
        """Recalculate statement data - useful for fixing existing statements"""
        return self.generate_statement_data()

    def check_missing_payments(self):
        """Check if there are payments that should be included but aren't"""
        # Get all payments in the period (excluding cancelled/refunded)
        all_payments = Payment.objects.filter(
            customer=self.customer,
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        ).exclude(status__in=['cancelled', 'refunded'])

        # Get payments currently in the statement
        current_payments = Payment.objects.filter(
            customer=self.customer,
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date,
            status='completed'
        )

        # Find missing payments
        missing_payments = all_payments.exclude(id__in=current_payments.values_list('id', flat=True))

        return {
            'total_payments': all_payments.count(),
            'included_payments': current_payments.count(),
            'missing_payments': missing_payments.count(),
            'missing_payment_list': missing_payments
        }

    def _calculate_balance_before_date(self, target_date):
        """Calculate customer balance before a specific date"""
        # Orders before date
        orders_before = Order.objects.filter(
            customer=self.customer,
            date__lt=target_date
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # Credits before date
        credits_before = CreditNote.objects.filter(
            customer=self.customer,
            created_at__date__lt=target_date
        ).aggregate(
            total=Sum('items__amount')
        )['total'] or Decimal('0.00')

        # Payments before date - include all active payments (completed, pending, but not cancelled/refunded)
        payments_before = Payment.objects.filter(
            customer=self.customer,
            payment_date__lt=target_date
        ).exclude(status__in=['cancelled', 'refunded']).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        return orders_before - credits_before - payments_before


class PaymentLog(models.Model):
    """Comprehensive payment activity logging"""
    LOG_ACTION_CHOICES = [
        ('payment_created', 'Payment Created'),
        ('payment_updated', 'Payment Updated'),
        ('payment_cancelled', 'Payment Cancelled'),
        ('allocation_created', 'Allocation Created'),
        ('allocation_updated', 'Allocation Updated'),
        ('allocation_deleted', 'Allocation Deleted'),
        ('balance_recalculated', 'Balance Recalculated'),
        ('statement_generated', 'Statement Generated'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=LOG_ACTION_CHOICES)
    user = models.CharField(max_length=100, blank=True)

    # Related objects
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    # Details
    details = models.TextField(default='{}')  # Store JSON as text for SQLite compatibility
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action']),
            models.Index(fields=['customer', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp}"


# Methods are now defined on their respective models to avoid monkey-patching

# Signals to automatically update customer balances
@receiver(post_save, sender=Payment)
def update_customer_balance_on_payment(sender, instance, created, **kwargs):
    """Update customer balance when a payment is created or updated"""
    if created or instance.status == 'completed':
        balance, created = CustomerBalance.objects.get_or_create(
            customer=instance.customer,
            defaults={'currency': instance.customer.preferred_currency}
        )
        balance.recalculate_balance()

@receiver(post_save, sender=PaymentAllocation)
def update_customer_balance_on_allocation(sender, instance, created, **kwargs):
    """Update customer balance when a payment allocation is created or updated"""
    balance, created = CustomerBalance.objects.get_or_create(
        customer=instance.payment.customer,
        defaults={'currency': instance.payment.customer.preferred_currency}
    )
    balance.recalculate_balance()

    # Update order status if it becomes fully paid
    order = instance.order
    if order.status == 'pending' and order.is_paid():
        order.status = 'paid'
        order.save(update_fields=['status'])

@receiver(post_save, sender=Order)
def update_customer_balance_on_order(sender, instance, created, **kwargs):
    """Update customer balance when an order is created or updated"""
    balance, created = CustomerBalance.objects.get_or_create(
        customer=instance.customer,
        defaults={'currency': instance.customer.preferred_currency}
    )
    balance.recalculate_balance()
