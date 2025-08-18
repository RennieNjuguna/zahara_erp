from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.template.response import TemplateResponse
from .models import Order, OrderItem, CustomerOrderDefaults
from .forms import OrderItemForm, OrderAdminForm

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemForm
    extra = 1  # Start with one empty item
    fields = ('product', 'stem_length_cm', 'boxes', 'stems_per_box', 'stems', 'price_per_stem', 'total_amount')
    readonly_fields = ('stems', 'total_amount')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add custom JavaScript for auto-populating prices
        formset.form.base_fields['product'].widget.attrs.update({
            'class': 'product-select',
            'data-url': '/admin/orders/orderitem/get-pricing/'
        })
        formset.form.base_fields['stem_length_cm'].widget.attrs.update({
            'class': 'stem-length-input'
        })
        formset.form.base_fields['price_per_stem'].widget.attrs.update({
            'class': 'price-input'
        })
        return formset

    def total_amount(self, obj):
        if obj.total_amount == 0:
            return format_html('<span style="color: red;">No price set</span>')
        return obj.total_amount
    total_amount.short_description = 'Total Amount'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    inlines = [OrderItemInline]
    list_display = ('invoice_code', 'customer', 'branch', 'date', 'total_amount', 'currency')
    list_filter = ('customer', 'branch', 'date')
    search_fields = ('invoice_code', 'customer__name')
    actions = ['update_prices_from_customer_pricing', 'sync_prices_to_customer_pricing']

    class Media:
        js = ('orders/js/filter_branches.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get-pricing/', self.admin_site.admin_view(self.get_pricing), name='get-pricing'),
            path('get-branches/', self.admin_site.admin_view(self.get_branches), name='get-branches'),
            path('get-defaults/', self.admin_site.admin_view(self.get_defaults), name='get-defaults'),
        ]
        return custom_urls + urls

    def get_pricing(self, request):
        """Get pricing for a customer-product-stem length combination"""
        customer_id = request.GET.get('customer_id')
        product_id = request.GET.get('product_id')
        stem_length = request.GET.get('stem_length')

        if customer_id and product_id and stem_length:
            try:
                from products.models import CustomerProductPrice
                pricing = CustomerProductPrice.objects.get(
                    customer_id=customer_id,
                    product_id=product_id,
                    stem_length_cm=stem_length
                )
                return JsonResponse({
                    'success': True,
                    'price': str(pricing.price_per_stem)
                })
            except CustomerProductPrice.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'price': None
                })

        return JsonResponse({
            'success': False,
            'price': None
        })

    def get_branches(self, request):
        """Get branches for a specific customer"""
        customer_id = request.GET.get('customer_id')
        if customer_id:
            try:
                from customers.models import Branch
                branches = Branch.objects.filter(customer_id=customer_id)
                return JsonResponse([{'id': b.id, 'name': b.name} for b in branches], safe=False)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse([], safe=False)

    def get_defaults(self, request):
        """Get default stem length and price for a customer-product combination"""
        if request.method == 'POST':
            customer_id = request.POST.get('customer_id')
            product_id = request.POST.get('product_id')

            try:
                from customers.models import Customer
                from products.models import Product
                customer = Customer.objects.get(id=customer_id)
                product = Product.objects.get(id=product_id)

                defaults = CustomerOrderDefaults.get_defaults(customer, product)

                if defaults:
                    return JsonResponse({
                        'success': True,
                        'stem_length_cm': defaults['stem_length_cm'],
                        'price_per_stem': str(defaults['price_per_stem'])
                    })
                else:
                    # Return product's default stem length if no customer defaults
                    return JsonResponse({
                        'success': True,
                        'stem_length_cm': product.stem_length_cm,
                        'price_per_stem': None
                    })

            except (Customer.DoesNotExist, Product.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Customer or product not found'
                })

        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # After saving inlines, recalculate total_amount
        form.instance.save()

    def update_prices_from_customer_pricing(self, request, queryset):
        updated_count = 0
        for order in queryset:
            if order.update_prices_from_customer_pricing():
                updated_count += 1

        if updated_count > 0:
            self.message_user(request, f"Updated prices for {updated_count} orders from customer pricing.")
        else:
            self.message_user(request, "No prices were updated.")

    update_prices_from_customer_pricing.short_description = "Update prices from customer pricing"

    def sync_prices_to_customer_pricing(self, request, queryset):
        synced_count = 0
        for order in queryset:
            synced_count += order.sync_prices_to_customer_pricing()

        if synced_count > 0:
            self.message_user(request, f"Synced {synced_count} prices to customer pricing.")
        else:
            self.message_user(request, "No prices were synced.")

    sync_prices_to_customer_pricing.short_description = "Sync order prices to customer pricing"

@admin.register(CustomerOrderDefaults)
class CustomerOrderDefaultsAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'stem_length_cm', 'price_per_stem', 'last_used')
    list_filter = ('customer', 'product', 'stem_length_cm')
    search_fields = ('customer__name', 'product__name')
    readonly_fields = ('last_used',)
