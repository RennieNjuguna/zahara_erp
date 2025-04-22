from django.db import models

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

class Branch(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    short_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.customer.name} - {self.name}"
