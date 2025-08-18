from django.contrib import admin
from .models import Product, CustomerProductPrice

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'stem_length_cm')
    list_filter = ('stem_length_cm',)
    search_fields = ('name',)

@admin.register(CustomerProductPrice)
class CustomerProductPriceAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'stem_length_cm', 'price_per_stem')
    list_filter = ('customer', 'product', 'stem_length_cm')
    search_fields = ('customer__name', 'product__name')
