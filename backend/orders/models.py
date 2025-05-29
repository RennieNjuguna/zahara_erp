from django.db import models
from django.utils import timezone
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice
from django.core.exceptions import ValidationError

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
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    currency = models.CharField(max_length=10, editable=False)
    invoice_code = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField(default=timezone.now)
    remarks = models.CharField(max_length=255, blank=True, null=True)

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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_code} - {self.customer.name}"

    def clean(self):
        if self.branch and self.branch.customer != self.customer:
            raise ValidationError("Selected branch does not belong to the selected customer.")
