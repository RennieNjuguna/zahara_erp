from django import forms
from .models import Order, OrderItem
from customers.models import Branch
from decimal import Decimal

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        exclude = ['stems', 'total_amount', 'currency', 'invoice_code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.none()

        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['branch'].queryset = Branch.objects.filter(customer_id=customer_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.customer:
            self.fields['branch'].queryset = Branch.objects.filter(customer=self.instance.customer)

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'stem_length_cm', 'boxes', 'stems_per_box', 'price_per_stem']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add JavaScript to auto-fill stem length and price when product changes
        self.fields['product'].widget.attrs.update({
            'class': 'product-select',
            'data-url': '/admin/orders/orderitem/get-defaults/'
        })
        self.fields['stem_length_cm'].widget.attrs.update({
            'class': 'stem-length-input'
        })
        self.fields['price_per_stem'].widget.attrs.update({
            'class': 'price-input'
        })

    def clean_price_per_stem(self):
        price = self.cleaned_data.get('price_per_stem')
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        boxes = cleaned_data.get('boxes')
        stems_per_box = cleaned_data.get('stems_per_box')
        price_per_stem = cleaned_data.get('price_per_stem')

        if boxes and stems_per_box:
            total_stems = boxes * stems_per_box
            if total_stems <= 0:
                raise forms.ValidationError("Total stems must be greater than 0.")

        return cleaned_data
