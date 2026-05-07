from django.db import models
from customers.models import Customer

class Product(models.Model):
    TAX_CODE_CHOICES = [
        ('A', '16%'),
        ('B', '8%'),
        ('C', '0% (Export/Zero-rated)'),
        ('D', 'Exempt'),
        ('E', '8%'),
    ]
    name = models.CharField(max_length=100)
    stem_length_cm = models.PositiveIntegerField(help_text="Stem length in centimeters")
    tax_code = models.CharField(max_length=1, choices=TAX_CODE_CHOICES, default='C', help_text="KRA Tax Code (usually C for export)")
    item_classification_code = models.CharField(max_length=50, blank=True, null=True, help_text="KRA Item Classification Code (if required)")

    def __str__(self):
        return self.name

class CustomerProductPrice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='product_prices')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='customer_prices')
    stem_length_cm = models.PositiveIntegerField(help_text="Stem length in centimeters")
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('customer', 'product', 'stem_length_cm')

    def __str__(self):
        return f"{self.customer.name} - {self.product.name} @ {self.stem_length_cm}cm: {self.price_per_stem}"

