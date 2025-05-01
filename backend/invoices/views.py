from django.shortcuts import render, get_object_or_404
from .models import Invoice

def invoice_detail(request, invoice_code):
    invoice = get_object_or_404(Invoice, invoice_code=invoice_code)
    return render(request, 'invoices/invoice_detail.html', {'invoice': invoice})
