from django.contrib import admin
from .models import Invoice
from django.utils.html import format_html

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('order', 'invoice_code', 'download_invoice')
    search_fields = ('invoice_code', 'order__invoice_code')

    def download_invoice(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">Download PDF</a>', obj.pdf_file.url)
        return "No PDF available"

    download_invoice.short_description = "Invoice PDF"
