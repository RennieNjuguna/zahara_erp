from django.contrib import admin
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
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

@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    inlines = [CreditNoteItemInline]
    list_display = ('code', 'order', 'title', 'created_at')
    list_filter = ('created_at', 'order__customer')
    search_fields = ('code', 'title', 'order__invoice_code')
    readonly_fields = ('code', 'created_at')

# Payment and PaymentAllocation admin classes have been moved to the payments app
