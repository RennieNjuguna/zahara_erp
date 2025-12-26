from django.contrib import admin
from .models import Invoice, CreditNote, CreditNoteItem

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_code', 'order', 'created_at')
    search_fields = ('invoice_code',)

class CreditNoteItemInline(admin.TabularInline):
    model = CreditNoteItem
    extra = 0
    fields = ('order_item', 'stems', 'amount', 'reason')
    readonly_fields = ('amount',) 

class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ('code', 'customer', 'status', 'total_amount', 'currency', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('code', 'customer__name', 'reason')
    inlines = [CreditNoteItemInline]
    readonly_fields = ('total_amount',) 

admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(CreditNote, CreditNoteAdmin)
