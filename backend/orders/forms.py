from django import forms
from .models import Order
from customers.models import Branch


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['branch'].queryset = Branch.objects.filter(customer_id=customer_id)
            except (ValueError, TypeError):
                self.fields['branch'].queryset = Branch.objects.none()
        elif self.instance.pk:
            self.fields['branch'].queryset = Branch.objects.filter(customer=self.instance.customer)
        else:
            self.fields['branch'].queryset = Branch.objects.none()
