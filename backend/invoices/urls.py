from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    path('<str:invoice_code>/', views.invoice_detail, name='invoice_detail'),
]
