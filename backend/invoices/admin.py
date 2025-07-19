from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.utils.html import format_html
from .models import Invoice, AccountStatement, CreditNote, CreditNoteItem, Payment, PaymentAllocation
from .utils import generate_account_statement_pdf

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('order', 'invoice_code', 'invoice_date', 'download_invoice')
    search_fields = ('invoice_code', 'order__invoice_code')

    def invoice_date(self, obj):
        return obj.order.date

    invoice_date.short_description = 'Date'

    def download_invoice(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">Download PDF</a>', obj.pdf_file.url)
        return "No PDF available"

    download_invoice.short_description = "Invoice PDF"

@admin.register(AccountStatement)
class AccountStatementAdmin(admin.ModelAdmin):
    list_display = ('customer', 'month', 'created_at', 'download_pdf_link')
    readonly_fields = ('created_at',)
    actions = ['download_statement']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate-pdf/<int:statement_id>/', self.admin_site.admin_view(self.generate_pdf), name='generate-accountstatement-pdf'),
        ]
        return custom_urls + urls

    def generate_pdf(self, request, statement_id):
        statement = AccountStatement.objects.get(pk=statement_id)
        pdf_data = generate_account_statement_pdf(statement)
        response = HttpResponse(pdf_data, content_type='application/pdf')
        filename = f"{statement.customer.name}_Account_Statement_{statement.month.strftime('%B_%Y')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def download_pdf_link(self, obj):
        return format_html('<a href="{}">Download PDF</a>', f'generate-pdf/{obj.id}/')

    download_pdf_link.short_description = 'Download PDF'

    def download_statement(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select one statement to download.", level='error')
            return
        statement = queryset.first()
        return self.generate_pdf(request, statement.id)

    download_statement.short_description = "Download selected PDF"

class CreditNoteItemInline(admin.TabularInline):
    model = CreditNoteItem
    extra = 1

@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    inlines = [CreditNoteItemInline]
    list_display = ('code', 'order', 'title', 'created_at')
    list_filter = ('created_at', 'order__customer')
    search_fields = ('code', 'title', 'order__invoice_code')
    readonly_fields = ('code', 'created_at')

class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 1

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    inlines = [PaymentAllocationInline]
    list_display = ('customer', 'amount', 'payment_date', 'payment_method', 'allocated_amount', 'unallocated_amount')
    list_filter = ('payment_method', 'payment_date', 'customer')
    search_fields = ('customer__name', 'reference', 'notes')
    readonly_fields = ('created_at',)

    def allocated_amount(self, obj):
        return obj.allocated_amount()
    allocated_amount.short_description = "Allocated"

    def unallocated_amount(self, obj):
        return obj.unallocated_amount()
    unallocated_amount.short_description = "Unallocated"

@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('payment', 'order', 'amount', 'allocated_at')
    list_filter = ('allocated_at', 'payment__customer')
    search_fields = ('payment__customer__name', 'order__invoice_code')
    readonly_fields = ('allocated_at',)
