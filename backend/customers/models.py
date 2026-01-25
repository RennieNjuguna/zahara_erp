from django.db import models
from django.db.models import Sum, Count


class Customer(models.Model):
    CURRENCY_CHOICES = [
        ('KSH', 'Kenyan Shilling'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
    ]

    name = models.CharField(max_length=100)
    short_code = models.CharField(max_length=10, unique=True)
    preferred_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    email = models.CharField(max_length=500, blank=True, null=True, help_text="Separate multiple emails with commas")
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    INVOICE_CODE_PREFERENCE_CHOICES = [
        ('branch', 'Branch Short Code (Default)'),
        ('customer', 'Customer Short Code'),
    ]
    invoice_code_preference = models.CharField(
        max_length=10, 
        choices=INVOICE_CODE_PREFERENCE_CHOICES, 
        default='branch',
        help_text="Choose whether to use the Customer's short code or the Branch's short code for invoice numbering."
    )

    def __str__(self):
        return self.name

    def get_order_statistics(self):
        """Get comprehensive order statistics for this customer"""
        orders = self.orders.all()

        return {
            'total_orders': orders.count(),
            'total_sales': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
            'pending_orders': orders.filter(status='pending').count(),
            'paid_orders': orders.filter(status='paid').count(),
            'claimed_orders': orders.filter(status='claim').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
        }

    def current_balance(self):
        """Get current balance for this customer using CustomerBalance"""
        from payments.models import CustomerBalance  # Local import to avoid circular dependency

        balance, created = CustomerBalance.objects.get_or_create(
            customer=self,
            defaults={'currency': self.preferred_currency}
        )
        if created:
            balance.recalculate_balance()
        return balance.current_balance

    def outstanding_amount(self):
        """Calculate total outstanding amount for this customer"""
        total_outstanding = 0
        for order in self.orders.all():
            total_outstanding += order.outstanding_amount()
        return total_outstanding

    def unallocated_payments(self):
        """Calculate total unallocated payments for this customer"""
        from payments.models import Payment
        from payments.models import PaymentAllocation
        
        # Get all completed payments
        total_payments = Payment.objects.filter(
            customer=self,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get total allocated amounts
        total_allocated = PaymentAllocation.objects.filter(
            payment__customer=self,
            payment__status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Unallocated = payments - allocated
        unallocated = total_payments - total_allocated
        return max(0, unallocated)  # Can't be negative

class Branch(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    short_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.customer.name} - {self.name}"
