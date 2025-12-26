from django import forms
from .models import CreditNote, CreditNoteItem
from orders.models import Order, OrderItem
from customers.models import Customer
from django.core.exceptions import ValidationError

class CreditNoteCustomerForm(forms.Form):
    """Step 1: Select Customer"""
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        help_text="Select the customer to create a credit note for."
    )

class CreditNoteOrdersForm(forms.Form):
    """Step 2: Select Orders"""
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False, # Could be creating a purely ad-hoc credit note? No, requirement says "linked to one or multiple orders"
        help_text="Select one or more orders to credit items from."
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        if customer:
            # Show recent orders? or all pending/paid orders?
            # User might want to credit an old paid order.
            self.fields['orders'].queryset = Order.objects.filter(
                customer=customer
            ).order_by('-date')

class CreditNoteItemForm(forms.ModelForm):
    """Form for a single credit note item"""
    selected = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'item-select'}))

    class Meta:
        model = CreditNoteItem
        fields = ['stems', 'amount', 'reason']
        widgets = {
            'stems': forms.NumberInput(attrs={'class': 'form-control stems-input', 'min': '0'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'step': '0.01'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.order_item = kwargs.pop('order_item', None)
        super().__init__(*args, **kwargs)
        if self.order_item:
            # Set max stems to available stems (ordered - already credited)
            # This logic needs to happen in the View to be robust, but good for UI.
            pass

CreditNoteItemFormSet = forms.formset_factory(CreditNoteItemForm, extra=0)
