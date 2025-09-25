from django.contrib import admin
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from django.db.models import Sum
from .models import Invoice, CreditNote, CreditNoteItem

from django.db import models

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


class CreditNoteItemInline(admin.TabularInline):
    model = CreditNoteItem
    extra = 1
    fields = ('order_item', 'stems_affected', 'credit_amount', 'reason')
    readonly_fields = ('credit_amount',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order_item__product')

@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    inlines = [CreditNoteItemInline]
    list_display = ('code', 'order', 'customer', 'title', 'total_credit_amount', 'status', 'credit_type', 'created_at')
    list_filter = ('status', 'credit_type', 'created_at', 'order__customer', 'currency')
    search_fields = ('code', 'title', 'reason', 'order__invoice_code', 'order__customer__name')
    readonly_fields = ('code', 'total_credit_amount', 'currency', 'created_at', 'updated_at', 'applied_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('order', 'code', 'title', 'reason')
        }),
        ('Credit Details', {
            'fields': ('total_credit_amount', 'currency', 'status', 'credit_type')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at', 'applied_at'),
            'classes': ('collapse',)
        }),
    )

    def customer(self, obj):
        return obj.order.customer.name if obj.order else ''
    customer.short_description = 'Customer'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__customer', 'created_by')

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if hasattr(instance, 'credit_note') and not instance.credit_note:
                instance.credit_note = form.instance
            instance.save()
        formset.save_m2m()

        # Recalculate total credit amount
        form.instance.total_credit_amount = form.instance.credit_note_items.aggregate(
            total=Sum('credit_amount')
        )['total'] or 0
        form.instance.save(update_fields=['total_credit_amount'])


@admin.register(CreditNoteItem)
class CreditNoteItemAdmin(admin.ModelAdmin):
    list_display = ('credit_note', 'order_item', 'product', 'stems_affected', 'credit_amount', 'reason')
    list_filter = ('credit_note__status', 'credit_note__created_at')
    search_fields = ('credit_note__code', 'order_item__product__name', 'reason')
    readonly_fields = ('credit_amount',)

    def product(self, obj):
        return obj.order_item.product.name if obj.order_item else ''
    product.short_description = 'Product'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'credit_note', 'order_item__product'
        )

# Payment and PaymentAllocation admin classes have been moved to the payments app
