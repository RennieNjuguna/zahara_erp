from django.contrib import admin
from .models import Customer, Branch
from payments.models import PaymentAllocation

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'preferred_currency', 'total_orders', 'total_amount', 'total_paid', 'total_outstanding')
    list_filter = ('preferred_currency', 'branches__name')
    search_fields = ('name', 'short_code')

    def total_orders(self, obj):
        return obj.orders.count()
    total_orders.short_description = "Total Orders"

    def total_amount(self, obj):
        total = sum(order.total_amount for order in obj.orders.all())
        return f"{total:.2f} {obj.preferred_currency}"
    total_amount.short_description = "Total Amount"

    def total_paid(self, obj):
        total_paid = sum(
            allocation.amount for allocation in PaymentAllocation.objects.filter(
                payment__customer=obj
            )
        )
        return f"{total_paid:.2f} {obj.preferred_currency}"
    total_paid.short_description = "Total Paid"

    def total_outstanding(self, obj):
        return f"{obj.outstanding_amount():.2f} {obj.preferred_currency}"
    total_outstanding.short_description = "Total Outstanding"

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'customer')
    search_fields = ('name', 'short_code', 'customer__name')
