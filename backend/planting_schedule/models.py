from django.db import models


class Crop(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    days_to_maturity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class FarmBlock(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('fallow', 'Fallow'),
        ('cleared', 'Cleared'),
        ('maintenance', 'Under Maintenance'),
    ]

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    area_acres = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.area_acres} acres)"

    class Meta:
        ordering = ['name']
