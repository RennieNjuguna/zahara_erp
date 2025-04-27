from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_code', 'order', 'created_at')
    search_fields = ('invoice_code', 'order__customer__name')
