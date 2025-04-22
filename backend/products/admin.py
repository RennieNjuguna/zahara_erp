from django.contrib import admin
from .models import Product, CustomerProductPrice

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(CustomerProductPrice)
class CustomerProductPriceAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'price_per_stem')
    list_filter = ('customer', 'product')
