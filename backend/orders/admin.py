from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # Start with one empty item
    fields = ('product', 'boxes', 'stems_per_box', 'stems', 'price_per_stem', 'total_amount')
    readonly_fields = ('stems', 'price_per_stem', 'total_amount')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('invoice_code', 'customer', 'branch', 'date', 'total_amount', 'currency')
    list_filter = ('customer', 'branch', 'date')
    search_fields = ('invoice_code', 'customer__name')
