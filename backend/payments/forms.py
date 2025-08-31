from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import AccountStatement

class CustomAccountStatementForm(forms.ModelForm):
    """Form for generating custom account statements"""

    statement_type = forms.ChoiceField(
        choices=AccountStatement.STATEMENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='reconciliation',
        help_text="Choose the type of statement to generate"
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Start date for the statement period"
    )

    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="End date for the statement period"
    )

    include_payments = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Include payments in the statement"
    )

    include_credits = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Include credit notes in the statement"
    )

    date_preset = forms.ChoiceField(
        choices=[
            ('', 'Custom Range'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_quarter', 'This Quarter'),
            ('last_quarter', 'Last Quarter'),
            ('this_year', 'This Year'),
            ('last_year', 'Last Year'),
        ],
        required=False,
        help_text="Quick date range selection"
    )

    class Meta:
        model = AccountStatement
        fields = ['customer', 'statement_type', 'start_date', 'end_date', 'include_payments', 'include_credits']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.now().date()
        self.fields['start_date'].initial = today.replace(day=1)
        self.fields['end_date'].initial = today

        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        statement_type = cleaned_data.get('statement_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        include_payments = cleaned_data.get('include_payments')
        include_credits = cleaned_data.get('include_credits')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date")

        if statement_type == 'reconciliation':
            cleaned_data['include_payments'] = True
            cleaned_data['include_credits'] = True

        # Allow no options selected for custom statements
        # if statement_type in ['periodic', 'full_history']:
        #     if not include_payments and not include_credits:
        #         raise forms.ValidationError(
        #             "For custom statements, you must include at least payments or credits"
        #         )

        return cleaned_data
