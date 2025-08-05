from django import forms
from .models import Order
from customers.models import Customer
from payments.models import Payment, PaymentAllocation

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
