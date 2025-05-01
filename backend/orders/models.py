from django.db import models
from django.utils import timezone
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stems = models.PositiveIntegerField()
    price_per_stem = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    currency = models.CharField(max_length=10, editable=False)
    invoice_code = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField(default=timezone.now)

    def save(self, *args, **kwargs):
        # 1. Fetch the correct price per stem
        try:
            cpp = CustomerProductPrice.objects.get(
                customer=self.customer,
                product=self.product
            )
            self.price_per_stem = cpp.price_per_stem
        except CustomerProductPrice.DoesNotExist:
            raise ValueError("Price for this customer-product combination is not defined.")

        # 2. Calculate total
        self.total_amount = self.stems * self.price_per_stem

        # 3. Get currency from customer
        self.currency = self.customer.preferred_currency

        # 4. Generate invoice code if not set
        if not self.invoice_code:
            short_code = self.branch.short_code if self.branch else self.customer.short_code
            count = Order.objects.filter(
                invoice_code__startswith=short_code
            ).count() + 1
            self.invoice_code = f"{short_code}{str(count).zfill(3)}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_code} - {self.customer.name} - {self.product.name}"
