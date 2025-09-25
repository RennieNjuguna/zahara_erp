from django import forms
from .models import CreditNote, CreditNoteItem
from orders.models import Order, OrderItem
from customers.models import Customer
from payments.models import Payment, PaymentAllocation
from django.core.exceptions import ValidationError
from decimal import Decimal

class CreditNoteForm(forms.Form):
    """Form for creating and editing credit notes"""

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all().order_by('name'),
        empty_label="Select a customer",
        required=True,
        help_text="Select the customer to see their orders",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    order = forms.CharField(
        required=False,
        help_text="Select the order for this credit note",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    title = forms.CharField(
        max_length=100,
        required=True,
        help_text="Brief title for the credit note",
        widget=forms.TextInput(attrs={'placeholder': 'Credit Note Title', 'class': 'form-control'})
    )

    reason = forms.CharField(
        required=True,
        help_text="Detailed reason for the credit note",
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the reason for the credit note (e.g., damaged items, quality issues, short delivery)', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set initial value for order field if provided
        if self.initial and 'order' in self.initial and self.initial['order']:
            self.fields['order'].initial = self.initial['order'].id

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        order = cleaned_data.get('order')

        if not customer:
            raise ValidationError("Please select a customer.")

        # Removed order validation - let the view handle it
        return cleaned_data


class CreditNoteItemForm(forms.ModelForm):
    """Form for individual credit note items"""

    class Meta:
        model = CreditNoteItem
        fields = ['order_item', 'stems_affected', 'reason']
        widgets = {
            'reason': forms.TextInput(attrs={'placeholder': 'Specific reason for this item credit'}),
        }

    def __init__(self, *args, **kwargs):
        credit_note = kwargs.pop('credit_note', None)
        super().__init__(*args, **kwargs)

        if credit_note and credit_note.order:
            # Filter order items to only show items from the selected order
            self.fields['order_item'].queryset = OrderItem.objects.filter(
                order=credit_note.order
            )

            # Add help text
            self.fields['order_item'].help_text = "Select the order item to credit"
            self.fields['stems_affected'].help_text = "Number of stems to credit"
            self.fields['reason'].help_text = "Specific reason for this item credit"


class CreditNoteItemFormSet(forms.BaseFormSet):
    """Formset for multiple credit note items"""

    def __init__(self, *args, **kwargs):
        self.credit_note = kwargs.pop('credit_note', None)
        super().__init__(*args, **kwargs)

        # Set form kwargs for each form in the formset
        for form in self.forms:
            form.credit_note = self.credit_note

    def clean(self):
        """Validate the formset"""
        super().clean()

        if not self.credit_note:
            raise ValidationError("Credit note is required")

        # Check if at least one item is provided
        if not any(form.cleaned_data for form in self.forms if form.cleaned_data):
            raise ValidationError("At least one credit note item is required")

        # Check for duplicate order items
        order_items = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                order_item = form.cleaned_data.get('order_item')
                if order_item:
                    if order_item in order_items:
                        raise ValidationError(f"Order item {order_item} is duplicated")
                    order_items.append(order_item)


class BulkCreditNoteForm(forms.Form):
    """Form for creating credit notes for multiple orders"""

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        label="Customer",
        help_text="Select customer to filter orders"
    )

    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.none(),
        label="Select Orders",
        widget=forms.CheckboxSelectMultiple,
        help_text="Select orders for credit notes"
    )

    title = forms.CharField(
        max_length=100,
        help_text="Title for the credit notes"
    )

    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Reason for the credit notes"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter orders based on customer selection
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['orders'].queryset = Order.objects.filter(
                    customer_id=customer_id,
                    status__in=['pending', 'paid']
                ).order_by('-date')
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        orders = cleaned_data.get('orders')

        if not orders:
            raise ValidationError("Please select at least one order")

        # Validate that all orders have the same currency
        currencies = set(order.currency for order in orders)
        if len(currencies) > 1:
            raise ValidationError("All orders must have the same currency")

        return cleaned_data


class CreditNoteSearchForm(forms.Form):
    """Form for searching and filtering credit notes"""

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        label="Customer",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    order = forms.ModelChoiceField(
        queryset=Order.objects.all(),
        required=False,
        label="Order",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + CreditNote.STATUS_CHOICES,
        required=False,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    credit_type = forms.ChoiceField(
        choices=[('', 'All Types')] + CreditNote.CREDIT_TYPE_CHOICES,
        required=False,
        label="Credit Type",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        required=False,
        label="From Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    date_to = forms.DateField(
        required=False,
        label="To Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter orders based on customer selection
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['order'].queryset = Order.objects.filter(
                    customer_id=customer_id
                )
            except (ValueError, TypeError):
                pass


class PaymentAllocationForm(forms.ModelForm):
    class Meta:
        model = PaymentAllocation
        fields = ['payment', 'order', 'amount']

    class Media:
        js = ('admin/js/payment_allocation.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].queryset = Order.objects.none()

        if 'payment' in self.data:
            try:
                payment_id = int(self.data.get('payment'))
                payment = Payment.objects.get(id=payment_id)
                self.fields['order'].queryset = Order.objects.filter(customer=payment.customer)
            except (ValueError, TypeError, Payment.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.payment:
            self.fields['order'].queryset = Order.objects.filter(customer=self.instance.payment.customer)

class BulkPaymentAllocationForm(forms.Form):
    payment = forms.ModelChoiceField(
        queryset=Payment.objects.all(),
        label="Select Payment"
    )
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        label="Customer"
    )
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.none(),
        label="Select Orders to Allocate Payment",
        widget=forms.CheckboxSelectMultiple
    )
    allocation_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="Amount to Allocate"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['orders'].queryset = Order.objects.filter(
                    customer_id=customer_id
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        payment = cleaned_data.get('payment')
        orders = cleaned_data.get('orders')
        allocation_amount = cleaned_data.get('allocation_amount')

        if payment and allocation_amount:
            if allocation_amount > payment.unallocated_amount():
                raise forms.ValidationError(
                    f"Allocation amount ({allocation_amount}) exceeds available payment amount ({payment.unallocated_amount()})"
                )

        if orders and allocation_amount:
            total_outstanding = sum(order.outstanding_amount() for order in orders)
            if allocation_amount > total_outstanding:
                raise forms.ValidationError(
                    f"Allocation amount ({allocation_amount}) exceeds total outstanding amount ({total_outstanding})"
                )

        return cleaned_data
