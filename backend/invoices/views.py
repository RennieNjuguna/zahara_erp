from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.forms import formset_factory
from django.urls import reverse
from .models import Invoice, CreditNote, CreditNoteItem
from .forms import (
    CreditNoteForm, CreditNoteItemForm, CreditNoteItemFormSet,
    BulkCreditNoteForm, CreditNoteSearchForm
)
from orders.models import Order, OrderItem
from customers.models import Customer
from payments.models import CustomerBalance
from decimal import Decimal
from django.core.exceptions import ValidationError


def invoice_detail(request, invoice_code):
    invoice = get_object_or_404(Invoice, invoice_code=invoice_code)
    return render(request, 'invoices/invoice_detail.html', {'invoice': invoice})


@login_required
def credit_note_list(request):
    """List all credit notes with search and filtering"""
    search_form = CreditNoteSearchForm(request.GET)
    credit_notes = CreditNote.objects.all()

    if search_form.is_valid():
        customer = search_form.cleaned_data.get('customer')
        order = search_form.cleaned_data.get('order')
        status = search_form.cleaned_data.get('status')
        credit_type = search_form.cleaned_data.get('credit_type')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if customer:
            credit_notes = credit_notes.filter(order__customer=customer)
        if order:
            credit_notes = credit_notes.filter(order=order)
        if status:
            credit_notes = credit_notes.filter(status=status)
        if credit_type:
            credit_notes = credit_notes.filter(credit_type=credit_type)
        if date_from:
            credit_notes = credit_notes.filter(created_at__date__gte=date_from)
        if date_to:
            credit_notes = credit_notes.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(credit_notes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'credit_notes': page_obj,
        'search_form': search_form,
        'total_credits': credit_notes.aggregate(total=Sum('total_credit_amount'))['total'] or 0,
    }
    return render(request, 'invoices/credit_note_list.html', context)


@login_required
def credit_note_detail(request, credit_note_id):
    """View credit note details"""
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)

    context = {
        'credit_note': credit_note,
        'credit_items': credit_note.credit_note_items.all(),
        'credit_summary': credit_note.get_credit_summary(),
    }
    return render(request, 'invoices/credit_note_detail.html', context)


@login_required
def credit_note_create(request):
    """Create a new credit note with items"""
    if request.method == 'POST':
        form = CreditNoteForm(request.POST)
        if form.is_valid():
            try:
                                # Get the order and validate it
                order_id = form.cleaned_data.get('order')
                customer = form.cleaned_data.get('customer')

                if not order_id:
                    messages.error(request, 'Please select an order.')
                    return redirect('invoices:credit_note_create')

                if not customer:
                    messages.error(request, 'Please select a customer.')
                    return redirect('invoices:credit_note_create')

                # Get the order object
                try:
                    order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    messages.error(request, 'Selected order does not exist.')
                    return redirect('invoices:credit_note_create')

                # Validate order-customer relationship
                if order.customer != customer:
                    messages.error(request, 'The selected order does not belong to the selected customer.')
                    return redirect('invoices:credit_note_create')

                # Generate credit note code based on order
                credit_note_code = f"CN-{order.invoice_code}"

                # Create the credit note directly without using form.save()
                credit_note = CreditNote.objects.create(
                    code=credit_note_code,
                    order=order,
                    title=form.cleaned_data['title'],
                    reason=form.cleaned_data['reason'],
                    currency=order.currency,
                    status='pending',
                    created_by=request.user,
                    total_credit_amount=0  # Will be updated below
                )

                # Set credit type based on order status
                if order.status == 'pending':
                    credit_note.credit_type = 'order_reduction'
                elif order.status == 'paid':
                    credit_note.credit_type = 'customer_credit'
                credit_note.save()

                # Calculate total credit amount from form data
                total_credit = 0
                credit_items_data = []

                # Get credit amounts from form data
                for key, value in request.POST.items():
                    if key.startswith('credit_amount_') and value and float(value) > 0:
                        item_id = key.replace('credit_amount_', '')
                        stems_to_credit = request.POST.get(f'stems_to_credit_{item_id}', 0)

                        if stems_to_credit and int(stems_to_credit) > 0:
                            try:
                                order_item = OrderItem.objects.get(id=item_id, order=order)
                                credit_amount = float(value)
                                total_credit += credit_amount

                                credit_items_data.append({
                                    'order_item': order_item,
                                    'stems_affected': int(stems_to_credit),
                                    'credit_amount': credit_amount,
                                    'reason': form.cleaned_data['reason']
                                })
                            except OrderItem.DoesNotExist:
                                continue

                if total_credit > 0:
                    credit_note.total_credit_amount = total_credit
                    credit_note.save()

                    # Create credit note items
                    for item_data in credit_items_data:
                        CreditNoteItem.objects.create(
                            credit_note=credit_note,
                            order_item=item_data['order_item'],
                            stems_affected=item_data['stems_affected'],
                            reason=item_data['reason']
                        )

                    # Apply credit based on order status
                    if order.status == 'pending':
                        # Reduce order total for pending orders
                        order.total_amount = max(0, order.total_amount - total_credit)
                        order.save()
                    elif order.status == 'paid':
                        # Add to customer balance for paid orders
                        customer_balance, created = CustomerBalance.objects.get_or_create(
                            customer=order.customer,
                            currency=order.currency,
                            defaults={'balance': 0}
                        )
                        customer_balance.balance += total_credit
                        customer_balance.save()

                    messages.success(request, f'Credit note {credit_note_code} created successfully with total credit of {total_credit} {order.currency}.')
                    return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)
                else:
                    # Delete the credit note if no valid credits
                    credit_note.delete()
                    messages.error(request, 'No valid credit amounts provided.')
                    return redirect('invoices:credit_note_create')

            except Exception as e:
                messages.error(request, f'Error creating credit note: {str(e)}')
                return redirect('invoices:credit_note_create')
    else:
        form = CreditNoteForm()

    context = {
        'form': form,
        'title': 'Create Credit Note',
        'customers': Customer.objects.all().order_by('name'),
    }
    return render(request, 'invoices/credit_note_form.html', context)


@login_required
def credit_note_add_items(request, credit_note_id):
    """Add items to a credit note"""
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)

    # Create formset for credit note items
    CreditNoteItemFormSetFactory = formset_factory(
        CreditNoteItemForm,
        extra=1,
        can_delete=True,
        formset=CreditNoteItemFormSet
    )

    if request.method == 'POST':
        formset = CreditNoteItemFormSetFactory(
            request.POST,
            credit_note=credit_note
        )
        if formset.is_valid():
            # Save credit note items
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    credit_item = form.save(commit=False)
                    credit_item.credit_note = credit_note
                    credit_item.save()

            messages.success(request, f'Credit note items added successfully.')
            return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)
    else:
        formset = CreditNoteItemFormSetFactory(credit_note=credit_note)

    context = {
        'credit_note': credit_note,
        'formset': formset,
        'order_items': credit_note.order.items.all(),
    }
    return render(request, 'invoices/credit_note_items_form.html', context)


@login_required
def credit_note_edit(request, credit_note_id):
    """Edit an existing credit note"""
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)

    if request.method == 'POST':
        form = CreditNoteForm(request.POST)
        if form.is_valid():
            # Update the credit note directly
            credit_note.title = form.cleaned_data['title']
            credit_note.reason = form.cleaned_data['reason']
            credit_note.save()
            messages.success(request, f'Credit note {credit_note.code} updated successfully.')
            return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)
    else:
        # Pre-populate form with existing data
        form = CreditNoteForm(initial={
            'customer': credit_note.order.customer,
            'order': credit_note.order,
            'title': credit_note.title,
            'reason': credit_note.reason,
        })

    context = {
        'form': form,
        'credit_note': credit_note,
        'title': 'Edit Credit Note',
    }
    return render(request, 'invoices/credit_note_form.html', context)


@login_required
def credit_note_cancel(request, credit_note_id):
    """Cancel a credit note"""
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)

    if request.method == 'POST':
        try:
            credit_note.cancel_credit()
            messages.success(request, f'Credit note {credit_note.code} cancelled successfully.')
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)

    context = {
        'credit_note': credit_note,
    }
    return render(request, 'invoices/credit_note_cancel_confirm.html', context)


@login_required
def bulk_credit_note_create(request):
    """Create credit notes for multiple orders"""
    if request.method == 'POST':
        form = BulkCreditNoteForm(request.POST)
        if form.is_valid():
            orders = form.cleaned_data['orders']
            title = form.cleaned_data['title']
            reason = form.cleaned_data['reason']

            created_credits = []
            for order in orders:
                credit_note = CreditNote.objects.create(
                    order=order,
                    title=title,
                    reason=reason,
                    created_by=request.user
                )
                created_credits.append(credit_note)

            messages.success(request, f'{len(created_credits)} credit notes created successfully.')
            return redirect('invoices:credit_note_list')
    else:
        form = BulkCreditNoteForm()

    context = {
        'form': form,
        'title': 'Create Bulk Credit Notes',
    }
    return render(request, 'invoices/bulk_credit_note_form.html', context)


@login_required
def get_order_items_ajax(request):
    """AJAX endpoint to get order items for credit note creation"""
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            items = order.items.all()
            data = []
            for item in items:
                # Calculate available stems (total - already credited)
                credited_stems = CreditNoteItem.objects.filter(
                    order_item=item
                ).aggregate(
                    total=Sum('stems_affected')
                )['total'] or 0
                available_stems = item.stems - credited_stems

                data.append({
                    'id': item.id,
                    'product_name': item.product.name,
                    'stems': item.stems,
                    'available_stems': available_stems,
                    'price_per_stem': str(item.price_per_stem),
                    'total_amount': str(item.total_amount),
                })
            return JsonResponse({'items': data})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    return JsonResponse({'error': 'Order ID required'}, status=400)


@login_required
def get_customer_orders_ajax(request):
    """AJAX endpoint to get customer orders for credit note creation"""
    customer_id = request.GET.get('customer_id')
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            orders = customer.orders.filter(
                status__in=['pending', 'paid']
            ).order_by('-date')
            data = []
            for order in orders:
                data.append({
                    'id': order.id,
                    'invoice_code': order.invoice_code,
                    'date': order.date.strftime('%Y-%m-%d'),
                    'status': order.status,  # Use raw status value, not display
                    'total_amount': str(order.total_amount),
                    'currency': order.currency,
                })
            return JsonResponse({'orders': data})
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)

    return JsonResponse({'error': 'Customer ID required'}, status=400)


@login_required
def credit_note_export(request, credit_note_id):
    """Export credit note as PDF"""
    credit_note = get_object_or_404(CreditNote, id=credit_note_id)

    # TODO: Implement PDF generation
    # For now, just redirect to detail view
    messages.info(request, 'PDF export functionality will be implemented soon.')
    return redirect('invoices:credit_note_detail', credit_note_id=credit_note.id)
