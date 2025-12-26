from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import CreditNote, CreditNoteItem
from .forms import CreditNoteCustomerForm, CreditNoteOrdersForm, CreditNoteItemFormSet
from orders.models import Order, OrderItem
from customers.models import Customer

@login_required
def invoice_detail(request, invoice_code):
    invoice = get_object_or_404(Invoice, invoice_code=invoice_code)
    return render(request, 'invoices/invoice_detail.html', {'invoice': invoice})

@login_required
def credit_note_list(request):
    credit_notes = CreditNote.objects.all()
    return render(request, 'invoices/credit_note_list.html', {'credit_notes': credit_notes})

@login_required
def credit_note_detail(request, credit_note_id):
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)
    return render(request, 'invoices/credit_note_detail.html', {'credit_note': credit_note})

@login_required
def credit_note_approve(request, credit_note_id):
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)
    if request.method == 'POST':
        try:
            credit_note.approve()
            messages.success(request, f"Credit Note {credit_note.code} approved successfully.")
        except Exception as e:
            messages.error(request, f"Error approving credit note: {e}")
    return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)

@login_required
def credit_note_create_step1(request):
    """Select Customer"""
    if request.method == 'POST':
        form = CreditNoteCustomerForm(request.POST)
        if form.is_valid():
            request.session['cn_customer_id'] = form.cleaned_data['customer'].id
            return redirect('invoices:credit_note_create_step2')
    else:
        form = CreditNoteCustomerForm()
    
    return render(request, 'invoices/credit_note_create_step1.html', {'form': form})

@login_required
def credit_note_create_step2(request):
    """Select Orders"""
    customer_id = request.session.get('cn_customer_id')
    if not customer_id:
        return redirect('invoices:credit_note_create_step1')
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CreditNoteOrdersForm(request.POST, customer=customer)
        if form.is_valid():
            selected_orders = form.cleaned_data['orders']
            request.session['cn_order_ids'] = [o.id for o in selected_orders]
            return redirect('invoices:credit_note_create_step3')
    else:
        form = CreditNoteOrdersForm(customer=customer)
    
    return render(request, 'invoices/credit_note_create_step2.html', {
        'form': form,
        'customer': customer
    })

@login_required
def credit_note_create_step3(request):
    """Select Items and Quantities"""
    customer_id = request.session.get('cn_customer_id')
    order_ids = request.session.get('cn_order_ids')
    
    if not customer_id or not order_ids:
        return redirect('invoices:credit_note_create_step1')
        
    customer = get_object_or_404(Customer, id=customer_id)
    orders = Order.objects.filter(id__in=order_ids)
    
    # Collect all items from selected orders
    all_order_items = []
    for order in orders:
        all_order_items.extend(order.items.all())
        
    if request.method == 'POST':
        formset = CreditNoteItemFormSet(request.POST)
        # We need to re-associate forms with order items to iterate securely?
        # Formset management with dynamic items is tricky.
        # A simpler approach: Look at the POST data directly or construct formset carefully.
        # Let's use the formset but we must ensure the order of items matches what we rendered.
        
        if formset.is_valid():
            # Create the Credit Note object
            credit_note = CreditNote.objects.create(
                customer=customer,
                reason=request.POST.get('global_reason', 'Multi-order credit'),
                created_by=request.user
            )
            
            has_items = False
            for i, form in enumerate(formset):
                if form.cleaned_data.get('selected'):
                    order_item = all_order_items[i]
                    stems = form.cleaned_data.get('stems')
                    amount = form.cleaned_data.get('amount')
                    reason = form.cleaned_data.get('reason')
                    
                    if stems > 0 or amount > 0:
                         CreditNoteItem.objects.create(
                            credit_note=credit_note,
                            order_item=order_item,
                            stems=stems or 0,
                            amount=amount or 0,
                            reason=reason
                        )
                         has_items = True

            if has_items:
                credit_note.calculate_total()
                messages.success(request, "Credit Note created successfully (Pending Approval).")
                # Clear session
                del request.session['cn_customer_id']
                del request.session['cn_order_ids']
                return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)
            else:
                credit_note.delete()
                messages.error(request, "No items were credited.")
    else:
        # Pre-populate formset with 0s
        initial_data = []
        for item in all_order_items:
            initial_data.append({
                'selected': False,
                'stems': 0,
                'amount': 0,
                'reason': ''
            })
        formset = CreditNoteItemFormSet(initial=initial_data)
    
    # Bundle items with forms for template rendering
    items_with_forms = zip(all_order_items, formset.forms)
    
    return render(request, 'invoices/credit_note_create_step3.html', {
        'formset': formset,
        'items_with_forms': items_with_forms,
        'customer': customer,
        'formset_management_form': formset.management_form
    })
