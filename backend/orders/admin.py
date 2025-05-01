from django.contrib import admin
from .models import Order
from .forms import OrderAdminForm

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = [
        'invoice_code', 'customer', 'branch', 'product',
        'boxes', 'stems_per_box', 'stems', 'total_amount', 'currency', 'date'
    ]

    class Media:
        js = ('admin/js/jquery.init.js', 'orders/js/filter_branches.js',)
