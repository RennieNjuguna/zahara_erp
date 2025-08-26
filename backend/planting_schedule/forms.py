from django import forms
from .models import Crop, FarmBlock


class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ['name', 'description', 'days_to_maturity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'days_to_maturity': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class FarmBlockForm(forms.ModelForm):
    class Meta:
        model = FarmBlock
        fields = ['name', 'description', 'area_acres', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
