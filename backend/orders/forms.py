from django import forms
from .models import Order
from customers.models import Branch

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        exclude = ['stems', 'price_per_stem', 'total_amount', 'currency', 'invoice_code']

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
