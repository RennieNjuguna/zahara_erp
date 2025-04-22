from django.db import models
from customers.models import Customer, Branch
from products.models import Product

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stems = models.PositiveIntegerField()
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    currency = models.CharField(max_length=3)
    invoice_code = models.CharField(max_length=20, unique=True)
    date = models.DateField()

    def save(self, *args, **kwargs):
        self.total_amount = self.stems * self.price_per_stem
        if not self.currency:
            self.currency = self.customer.preferred_currency
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.invoice_code} - {self.customer.name}"
