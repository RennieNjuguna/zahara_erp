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

class Branch(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    short_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.customer.name} - {self.name}"
