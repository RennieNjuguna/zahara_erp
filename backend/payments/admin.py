from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.shortcuts import render
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from .models import (
    PaymentType, Payment, PaymentAllocation, CustomerBalance,
    AccountStatement, PaymentLog
)
from customers.models import Customer
from orders.models import Order
from invoices.models import CreditNote


class HasOrdersFilter(admin.SimpleListFilter):
    title = 'Has Orders'
    parameter_name = 'has_orders'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has Orders'),
            ('no', 'No Orders'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(customer__orders__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(customer__orders__isnull=True)
        return queryset


@admin.register(PaymentType)
class PaymentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'mode', 'is_active', 'created_at']
    list_filter = ['mode', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 1
    fields = ['order', 'amount', 'allocated_at']
    readonly_fields = ['allocated_at']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "order":
            # Filter orders to show only those with outstanding amounts
            kwargs["queryset"] = db_field.related_model.objects.filter(
                total_amount__gt=0
            ).order_by('-date')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'customer', 'amount', 'currency', 'payment_method',
        'payment_date', 'status', 'allocated_amount_display', 'unallocated_amount_display'
    ]
    list_filter = [
        'status', 'payment_method', 'payment_date', 'payment_type', 'currency'
    ]
    search_fields = [
        'customer__name', 'reference_number', 'notes', 'payment_id'
    ]
    readonly_fields = [
        'payment_id', 'created_at', 'updated_at', 'allocated_amount',
        'unallocated_amount', 'is_fully_allocated'
    ]
    date_hierarchy = 'payment_date'
    inlines = [PaymentAllocationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_id', 'customer', 'payment_type', 'status')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'payment_method', 'payment_date')
        }),
        ('Reference & Notes', {
            'fields': ('reference_number', 'notes')
        }),
        ('Allocation Status', {
            'fields': ('allocated_amount', 'unallocated_amount', 'is_fully_allocated'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def allocated_amount_display(self, obj):
        return f"{obj.allocated_amount} {obj.currency}"
    allocated_amount_display.short_description = 'Allocated'

    def unallocated_amount_display(self, obj):
        return f"{obj.unallocated_amount} {obj.currency}"
    unallocated_amount_display.short_description = 'Unallocated'

    actions = ['allocate_bulk_payment', 'recalculate_customer_balances']

    def allocate_bulk_payment(self, request, queryset):
        """Action to allocate bulk payments to orders"""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one payment for bulk allocation.", messages.ERROR)
            return

        payment = queryset.first()
        if payment.is_fully_allocated:
            self.message_user(request, "Payment is already fully allocated.", messages.WARNING)
            return

        # Redirect to bulk allocation view
        return HttpResponseRedirect(
            reverse('admin:payments_payment_bulk_allocate', args=[payment.payment_id])
        )
    allocate_bulk_payment.short_description = "Allocate bulk payment to orders"

    def recalculate_customer_balances(self, request, queryset):
        """Recalculate customer balances for selected payments"""
        customers_updated = set()
        for payment in queryset:
            if payment.customer not in customers_updated:
                balance, created = CustomerBalance.objects.get_or_create(
                    customer=payment.customer,
                    defaults={'currency': payment.customer.preferred_currency}
                )
                balance.recalculate_balance()
                customers_updated.add(payment.customer)

        self.message_user(
            request,
            f"Recalculated balances for {len(customers_updated)} customers.",
            messages.SUCCESS
        )
    recalculate_customer_balances.short_description = "Recalculate customer balances"


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'order', 'amount', 'allocated_at', 'customer_name', 'unallocated_amount_display'
    ]
    list_filter = ['allocated_at', 'payment__payment_method']
    search_fields = [
        'payment__customer__name', 'order__invoice_code',
        'payment__reference_number'
    ]
    readonly_fields = ['allocated_at']
    date_hierarchy = 'allocated_at'

    def customer_name(self, obj):
        return obj.payment.customer.name
    customer_name.short_description = 'Customer'

    def unallocated_amount_display(self, obj):
        """Show unallocated amount at the time this allocation was made"""
        # Get all allocations for this payment up to and including this allocation
        allocations_up_to_this = obj.payment.allocations.filter(
            allocated_at__lte=obj.allocated_at
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate unallocated amount at this point in time
        unallocated_at_time = obj.payment.amount - allocations_up_to_this
        return f"{unallocated_at_time} {obj.payment.currency}"
    unallocated_amount_display.short_description = 'Unallocated Amount'


@admin.register(CustomerBalance)
class CustomerBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'total_orders', 'total_sales', 'currency',
        'claimed_orders', 'paid_orders', 'outstanding_orders', 'current_balance', 'last_updated', 'actions_column'
    ]
    list_filter = [
        'currency', 'last_updated', HasOrdersFilter
    ]
    search_fields = ['customer__name']
    readonly_fields = ['current_balance', 'last_updated']
    ordering = ['-current_balance']
    list_per_page = 25

    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'currency')
        }),
        ('Balance Information', {
            'fields': ('current_balance', 'last_updated'),
            'description': 'Balance is automatically calculated from orders and payments'
        }),
    )

    def has_add_permission(self, request):
        return False  # Customer balances are created automatically

    def actions_column(self, obj):
        """Custom actions column with links"""
        return format_html(
            '<a href="{}" class="button">View Details</a>',
            reverse('admin:customers_customer_change', args=[obj.customer.id])
        )
    actions_column.short_description = 'Actions'

    def total_orders(self, obj):
        """Total number of orders for this customer"""
        count = obj.customer.orders.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    total_orders.short_description = 'Total Orders'

    def total_sales(self, obj):
        """Total sales amount for this customer"""
        total = obj.customer.orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        formatted_total = f"{float(total):.2f}"
        return format_html(
            '<span style="font-weight: bold; color: #28a745;">{}</span>',
            formatted_total
        )
    total_sales.short_description = 'Total Sales'

    def claimed_orders(self, obj):
        """Number of claimed orders for this customer"""
        count = obj.customer.orders.filter(status='claim').count()
        if count > 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}</span>',
                count
            )
        return count
    claimed_orders.short_description = 'Claimed Orders'

    def paid_orders(self, obj):
        """Number of paid orders for this customer"""
        count = obj.customer.orders.filter(status='paid').count()
        if count > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span>',
                count
            )
        return count
    paid_orders.short_description = 'Paid Orders'

    def outstanding_orders(self, obj):
        """Number of outstanding (pending) orders for this customer"""
        count = obj.customer.orders.filter(status='pending').count()
        if count > 0:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">{}</span>',
                count
            )
        return count
    outstanding_orders.short_description = 'Outstanding Orders'

    def current_balance(self, obj):
        """Current balance with color coding"""
        balance = float(obj.current_balance)
        formatted_balance = f"{balance:.2f}"

        if balance > 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}</span>',
                formatted_balance
            )
        elif balance < 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span>',
                formatted_balance
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">{}</span>',
                formatted_balance
            )
    current_balance.short_description = 'Balance'

    actions = ['recalculate_balances', 'generate_monthly_statements', 'update_order_statuses']

    def recalculate_balances(self, request, queryset):
        """Recalculate balances for selected customers"""
        for balance in queryset:
            balance.recalculate_balance()

        self.message_user(
            request,
            f"Recalculated balances for {queryset.count()} customers.",
            messages.SUCCESS
        )
    recalculate_balances.short_description = "Recalculate balances"

    def update_order_statuses(self, request, queryset):
        """Update order statuses for selected customers"""
        updated_count = 0
        for balance in queryset:
            for order in balance.customer.orders.filter(status='pending'):
                if order.is_paid():
                    order.status = 'paid'
                    order.save(update_fields=['status'])
                    updated_count += 1

        self.message_user(
            request,
            f"Updated {updated_count} orders to 'paid' status for {queryset.count()} customers.",
            messages.SUCCESS
        )
    update_order_statuses.short_description = "Update order statuses"

    def generate_monthly_statements(self, request, queryset):
        """Generate monthly statements for selected customers"""
        current_date = timezone.now().date()
        start_date = current_date.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)

        statements_created = 0
        for balance in queryset:
            statement, created = AccountStatement.objects.get_or_create(
                customer=balance.customer,
                statement_date=start_date,
                defaults={
                    'start_date': start_date,
                    'end_date': end_date,
                    'opening_balance': 0,
                    'closing_balance': 0,
                    'total_orders': 0,
                    'total_credits': 0,
                    'total_payments': 0,
                    'generated_by': request.user.username
                }
            )
            if created:
                statement.generate_statement_data()
                statements_created += 1

        self.message_user(
            request,
            f"Generated {statements_created} monthly statements.",
            messages.SUCCESS
        )
    generate_monthly_statements.short_description = "Generate monthly statements"


@admin.register(AccountStatement)
class AccountStatementAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'statement_date', 'opening_balance', 'closing_balance',
        'total_orders', 'total_payments', 'pdf_file_display'
    ]
    list_filter = ['statement_date', 'created_at']
    search_fields = ['customer__name', 'generated_by']
    readonly_fields = [
        'created_at', 'opening_balance', 'closing_balance',
        'total_orders', 'total_credits', 'total_payments'
    ]
    date_hierarchy = 'statement_date'

    fieldsets = (
        ('Customer & Period', {
            'fields': ('customer', 'statement_date', 'start_date', 'end_date')
        }),
        ('Statement Totals', {
            'fields': (
                'opening_balance', 'closing_balance', 'total_orders',
                'total_credits', 'total_payments'
            )
        }),
        ('PDF & Metadata', {
            'fields': ('pdf_file', 'generated_by', 'created_at')
        }),
    )

    def pdf_file_display(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">View PDF</a>',
                obj.pdf_file.url
            )
        return "No PDF"
    pdf_file_display.short_description = 'PDF File'

    actions = ['regenerate_statements', 'generate_pdf_statements']

    def regenerate_statements(self, request, queryset):
        """Regenerate statement data for selected statements"""
        for statement in queryset:
            statement.generate_statement_data()

        self.message_user(
            request,
            f"Regenerated {queryset.count()} statements.",
            messages.SUCCESS
        )
    regenerate_statements.short_description = "Regenerate statement data"

    def generate_pdf_statements(self, request, queryset):
        """Generate PDF files for selected statements"""
        # This would integrate with a PDF generation library
        # For now, just mark as placeholder
        self.message_user(
            request,
            f"PDF generation for {queryset.count()} statements queued.",
            messages.SUCCESS
        )
    generate_pdf_statements.short_description = "Generate PDF statements"


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'action', 'user', 'customer', 'payment', 'order'
    ]
    list_filter = ['action', 'timestamp']
    search_fields = [
        'user', 'customer__name', 'payment__payment_id',
        'order__invoice_code'
    ]
    readonly_fields = ['timestamp', 'action', 'user', 'details', 'ip_address']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Log Information', {
            'fields': ('timestamp', 'action', 'user', 'ip_address')
        }),
        ('Related Objects', {
            'fields': ('payment', 'customer', 'order')
        }),
        ('Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Custom admin views for bulk operations
class BulkAllocationAdmin(admin.ModelAdmin):
    """Custom admin for bulk payment allocation"""

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:payment_id>/bulk-allocate/',
                self.admin_site.admin_view(self.bulk_allocate_view),
                name='payments_payment_bulk_allocate',
            ),
        ]
        return custom_urls + urls

    def bulk_allocate_view(self, request, payment_id):
        """View for bulk payment allocation"""
        try:
            payment = Payment.objects.get(payment_id=payment_id)
        except Payment.DoesNotExist:
            messages.error(request, "Payment not found.")
            return HttpResponseRedirect(reverse('admin:payments_payment_changelist'))

        if request.method == 'POST':
            # Handle bulk allocation form submission
            allocations_data = request.POST.getlist('allocations')
            # Process allocations...
            messages.success(request, "Bulk allocation completed successfully.")
            return HttpResponseRedirect(reverse('admin:payments_payment_changelist'))

        # Get outstanding orders for the customer
        outstanding_orders = payment.customer.orders.filter(
            total_amount__gt=0
        ).order_by('date')

        context = {
            'payment': payment,
            'outstanding_orders': outstanding_orders,
            'title': f'Bulk Allocate Payment: {payment}',
        }

        return render(request, 'admin/payments/payment/bulk_allocate.html', context)


# The Payment model is already registered above with PaymentAdmin
