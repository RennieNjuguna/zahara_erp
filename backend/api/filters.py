import django_filters
from django.db.models import Q
from .models import Customer, Order, Payment, Expense, Employee
from customers.models import Customer as CustomerModel
from orders.models import Order as OrderModel
from payments.models import Payment as PaymentModel
from expenses.models import Expense as ExpenseModel
from employees.models import Employee as EmployeeModel


class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    short_code = django_filters.CharFilter(lookup_expr='icontains')
    preferred_currency = django_filters.ChoiceFilter(choices=CustomerModel.CURRENCY_CHOICES)
    has_outstanding_balance = django_filters.BooleanFilter(method='filter_outstanding_balance')

    class Meta:
        model = CustomerModel
        fields = ['name', 'short_code', 'preferred_currency']

    def filter_outstanding_balance(self, queryset, name, value):
        if value:
            return queryset.filter(
                orders__status__in=['pending', 'paid']
            ).distinct()
        return queryset


class OrderFilter(django_filters.FilterSet):
    invoice_code = django_filters.CharFilter(lookup_expr='icontains')
    customer = django_filters.ModelChoiceFilter(queryset=CustomerModel.objects.all())
    status = django_filters.ChoiceFilter(choices=OrderModel.STATUS_CHOICES)
    currency = django_filters.ChoiceFilter(choices=CustomerModel.CURRENCY_CHOICES)
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    amount_min = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    has_outstanding = django_filters.BooleanFilter(method='filter_outstanding')
    delivery_status = django_filters.ChoiceFilter(choices=OrderModel.DELIVERY_STATUS_CHOICES)

    class Meta:
        model = OrderModel
        fields = ['customer', 'status', 'currency', 'delivery_status']

    def filter_outstanding(self, queryset, name, value):
        if value:
            # Orders with outstanding amounts
            return queryset.filter(
                status__in=['pending', 'paid']
            ).exclude(
                total_amount=0
            ).distinct()
        return queryset


class PaymentFilter(django_filters.FilterSet):
    customer = django_filters.ModelChoiceFilter(queryset=CustomerModel.objects.all())
    payment_type = django_filters.ModelChoiceFilter(queryset=PaymentModel.payment_type.field.related_model.objects.all())
    payment_method = django_filters.ChoiceFilter(choices=PaymentModel.PAYMENT_METHOD_CHOICES)
    status = django_filters.ChoiceFilter(choices=PaymentModel.STATUS_CHOICES)
    currency = django_filters.ChoiceFilter(choices=CustomerModel.CURRENCY_CHOICES)
    date_from = django_filters.DateFilter(field_name='payment_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='payment_date', lookup_expr='lte')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    reference_number = django_filters.CharFilter(lookup_expr='icontains')
    is_allocated = django_filters.BooleanFilter(method='filter_allocated')

    class Meta:
        model = PaymentModel
        fields = ['customer', 'payment_type', 'payment_method', 'status', 'currency']

    def filter_allocated(self, queryset, name, value):
        if value is not None:
            if value:
                # Fully allocated payments
                return queryset.filter(
                    amount=F('allocated_amount')
                )
            else:
                # Unallocated payments
                return queryset.filter(
                    allocated_amount__lt=F('amount')
                )
        return queryset


class ExpenseFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(queryset=ExpenseModel.category.field.related_model.objects.all())
    status = django_filters.ChoiceFilter(choices=ExpenseModel.STATUS_CHOICES)
    currency = django_filters.ChoiceFilter(choices=CustomerModel.CURRENCY_CHOICES)
    date_from = django_filters.DateFilter(field_name='date_incurred', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date_incurred', lookup_expr='lte')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    reference_number = django_filters.CharFilter(lookup_expr='icontains')
    vendor_name = django_filters.CharFilter(lookup_expr='icontains')
    is_recurring = django_filters.BooleanFilter()

    class Meta:
        model = ExpenseModel
        fields = ['category', 'status', 'currency', 'is_recurring']


class EmployeeFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    position = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = EmployeeModel
        fields = ['first_name', 'last_name', 'position', 'email']


class CreditNoteFilter(django_filters.FilterSet):
    code = django_filters.CharFilter(lookup_expr='icontains')
    title = django_filters.CharFilter(lookup_expr='icontains')
    reason = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=['pending', 'applied', 'cancelled'])
    credit_type = django_filters.ChoiceFilter(choices=['order_reduction', 'customer_credit'])
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = None  # Will be set in views
        fields = ['code', 'title', 'reason', 'status', 'credit_type']


class AccountStatementFilter(django_filters.FilterSet):
    customer = django_filters.ModelChoiceFilter(queryset=CustomerModel.objects.all())
    statement_type = django_filters.ChoiceFilter(choices=['monthly', 'custom'])
    date_from = django_filters.DateFilter(field_name='statement_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='statement_date', lookup_expr='lte')

    class Meta:
        model = None  # Will be set in views
        fields = ['customer', 'statement_type']

