from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Order
from .forms import OrderAdminForm


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = ['invoice_code', 'customer', 'branch', 'product', 'stems', 'total_amount', 'currency', 'date']

    class Media:
        js = ('admin/js/jquery.init.js', 'orders/js/filter_branches.js',)
