from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Expense, ExpenseCategory, ExpenseAttachment
from django.utils import timezone


class ExpenseAttachmentInline(admin.TabularInline):
    """Inline attachments for expenses"""
    model = ExpenseAttachment
    extra = 1
    fields = ['file', 'file_type', 'description']
    readonly_fields = ['uploaded_at']


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """Admin interface for expense categories"""
    list_display = ['name', 'description', 'color_display', 'is_active', 'expense_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

    def color_display(self, obj):
        """Display color as a colored square"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'

    def expense_count(self, obj):
        """Count of expenses in this category"""
        return obj.expenses.count()
    expense_count.short_description = 'Expenses'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin interface for expenses"""
    list_display = [
        'name', 'amount', 'currency', 'category', 'date_incurred',
        'vendor_name', 'attachment_count', 'created_at'
    ]
    list_filter = [
        'currency', 'category', 'is_recurring', 'date_incurred',
        'created_at'
    ]
    search_fields = [
        'name', 'description', 'reference_number', 'vendor_name', 'tags'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'is_overdue', 'days_overdue'
    ]
    date_hierarchy = 'date_incurred'
    ordering = ['-date_incurred', '-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'amount', 'currency', 'reference_number', 'description')
        }),
        ('Categorization', {
            'fields': ('category', 'tags', 'is_recurring', 'recurring_frequency')
        }),
        ('Timing', {
            'fields': ('date_incurred', 'due_date')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_date')
        }),
        ('Vendor Information', {
            'fields': ('vendor_name', 'vendor_contact')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ExpenseAttachmentInline]

    def attachment_count(self, obj):
        """Count of attachments for this expense"""
        count = obj.attachments.count()
        if count > 0:
            return format_html(
                '<a href="{}?expense__id__exact={}">{} attachment{}</a>',
                reverse('admin:expenses_expenseattachment_changelist'),
                obj.id,
                count,
                's' if count != 1 else ''
            )
        return '0'
    attachment_count.short_description = 'Attachments'

    def is_overdue(self, obj):
        """Check if expense is overdue"""
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'

    def days_overdue(self, obj):
        """Get days overdue"""
        return obj.get_days_overdue()
    days_overdue.short_description = 'Days Overdue'


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for expense attachments"""
    list_display = [
        'expense', 'file_type', 'original_filename', 'file_preview',
        'uploaded_at'
    ]
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['expense__name', 'original_filename', 'description']
    readonly_fields = ['uploaded_at', 'file_extension', 'is_image', 'is_pdf']
    ordering = ['-uploaded_at']

    fieldsets = (
        ('File Information', {
            'fields': ('expense', 'file', 'file_type', 'description')
        }),
        ('File Details', {
            'fields': ('original_filename', 'file_extension', 'is_image', 'is_pdf'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )

    def file_preview(self, obj):
        """Show file preview or icon"""
        if obj.is_image():
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                obj.file.url
            )
        elif obj.is_pdf():
            return format_html(
                '<span style="color: red; font-size: 20px;">📄</span> PDF'
            )
        else:
            return format_html(
                '<span style="color: blue; font-size: 20px;">📎</span> {}',
                obj.get_file_extension().upper()
            )
    file_preview.short_description = 'Preview'

    def file_extension(self, obj):
        """Get file extension"""
        return obj.get_file_extension()
    file_extension.short_description = 'File Extension'

    def is_image(self, obj):
        """Check if file is image"""
        return obj.is_image()
    is_image.boolean = True
    is_image.short_description = 'Is Image'

    def is_pdf(self, obj):
        """Check if file is PDF"""
        return obj.is_pdf()
    is_pdf.boolean = True
    is_pdf.short_description = 'Is PDF'
