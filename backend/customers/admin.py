from django.contrib import admin
from .models import Customer, Branch
from payments.models import PaymentAllocation

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'preferred_currency', 'total_orders', 'total_amount', 'total_paid', 'net_balance', 'unallocated_amount')
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

    def net_balance(self, obj):
        balance = obj.current_balance()
        if balance > 0:
            return f"+{balance:.2f} {obj.preferred_currency} (Owed to you)"
        elif balance < 0:
            return f"{balance:.2f} {obj.preferred_currency} (You owe)"
        else:
            return f"0.00 {obj.preferred_currency} (Settled)"
    net_balance.short_description = "Net Balance"

    def unallocated_amount(self, obj):
        unallocated = obj.unallocated_payments()
        if unallocated > 0:
            return f"{unallocated:.2f} {obj.preferred_currency} (⚠️ Unallocated)"
        else:
            return f"0.00 {obj.preferred_currency} (✅ Allocated)"
    unallocated_amount.short_description = "Unallocated Amount"

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'customer')
    search_fields = ('name', 'short_code', 'customer__name')
