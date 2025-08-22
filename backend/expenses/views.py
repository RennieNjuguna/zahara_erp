from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Expense, ExpenseCategory, ExpenseAttachment


def expense_list(request):
    """Display list of all expenses with search and filtering"""
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    currency_filter = request.GET.get('currency', '')
    
    expenses = Expense.objects.select_related('category').prefetch_related('attachments').all()
    
    # Apply filters
    if search_query:
        expenses = expenses.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(vendor_name__icontains=search_query)
        )
    
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    
    if status_filter:
        expenses = expenses.filter(status=status_filter)
    
    if currency_filter:
        expenses = expenses.filter(currency=currency_filter)
    
    # Get filter options
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    currencies = Expense.CURRENCY_CHOICES
    statuses = Expense.STATUS_CHOICES
    
    # Calculate totals by currency
    totals_by_currency = {}
    for currency_code, currency_name in currencies:
        total = expenses.filter(currency=currency_code).aggregate(
            total=Sum('amount')
        )['total'] or 0
        totals_by_currency[currency_code] = total
    
    # Pagination
    paginator = Paginator(expenses.order_by('-date_incurred'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'currency_filter': currency_filter,
        'categories': categories,
        'currencies': currencies,
        'statuses': statuses,
        'totals_by_currency': totals_by_currency,
        'total_expenses': expenses.count(),
    }
    return render(request, 'expenses/expense_list.html', context)


def expense_detail(request, expense_id):
    """Display detailed information about a specific expense"""
    expense = get_object_or_404(Expense.objects.select_related('category').prefetch_related('attachments'), id=expense_id)
    
    context = {
        'expense': expense,
    }
    return render(request, 'expenses/expense_detail.html', context)


def expense_create(request):
    """Create a new expense"""
    if request.method == 'POST':
        # Extract form data
        name = request.POST.get('name')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency')
        reference_number = request.POST.get('reference_number')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        date_incurred = request.POST.get('date_incurred')
        vendor_name = request.POST.get('vendor_name')
        created_by = request.POST.get('created_by')
        
        if name and amount and currency and date_incurred:
            try:
                # Create expense
                expense = Expense.objects.create(
                    name=name,
                    amount=amount,
                    currency=currency,
                    reference_number=reference_number,
                    category_id=category_id if category_id else None,
                    description=description,
                    date_incurred=date_incurred,
                    vendor_name=vendor_name,
                    created_by=created_by
                )
                
                # Handle file uploads
                files = request.FILES.getlist('attachments')
                for uploaded_file in files:
                    ExpenseAttachment.objects.create(
                        expense=expense,
                        file=uploaded_file,
                        original_filename=uploaded_file.name
                    )
                
                messages.success(request, f'Expense "{expense.name}" created successfully!')
                return redirect('expenses:expense_detail', expense_id=expense.id)
                
            except Exception as e:
                messages.error(request, f'Error creating expense: {str(e)}')
        else:
            messages.error(request, 'Name, amount, currency, and date incurred are required.')
    
    # Get categories for form
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'categories': categories,
        'currencies': Expense.CURRENCY_CHOICES,
        'statuses': Expense.STATUS_CHOICES,
    }
    return render(request, 'expenses/expense_form.html', context)


def expense_edit(request, expense_id):
    """Edit an existing expense"""
    expense = get_object_or_404(Expense.objects.select_related('category').prefetch_related('attachments'), id=expense_id)
    
    if request.method == 'POST':
        # Extract form data
        name = request.POST.get('name')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency')
        reference_number = request.POST.get('reference_number')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        date_incurred = request.POST.get('date_incurred')
        vendor_name = request.POST.get('vendor_name')
        
        if name and amount and currency and date_incurred:
            try:
                # Update expense
                expense.name = name
                expense.amount = amount
                expense.currency = currency
                expense.reference_number = reference_number
                expense.category_id = category_id if category_id else None
                expense.description = description
                expense.date_incurred = date_incurred
                expense.vendor_name = vendor_name
                expense.save()
                
                # Handle new file uploads
                files = request.FILES.getlist('attachments')
                for uploaded_file in files:
                    ExpenseAttachment.objects.create(
                        expense=expense,
                        file=uploaded_file,
                        original_filename=uploaded_file.name
                    )
                
                messages.success(request, f'Expense "{expense.name}" updated successfully!')
                return redirect('expenses:expense_detail', expense_id=expense.id)
                
            except Exception as e:
                messages.error(request, f'Error updating expense: {str(e)}')
        else:
            messages.error(request, 'Name, amount, currency, and date incurred are required.')
    
    # Get categories for form
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'expense': expense,
        'categories': categories,
        'currencies': Expense.CURRENCY_CHOICES,
        'statuses': Expense.STATUS_CHOICES,
    }
    return render(request, 'expenses/expense_form.html', context)


def expense_delete(request, expense_id):
    """Delete an expense"""
    expense = get_object_or_404(Expense, id=expense_id)
    
    if request.method == 'POST':
        try:
            expense_name = expense.name
            expense.delete()
            messages.success(request, f'Expense "{expense_name}" deleted successfully!')
            return redirect('expenses:expense_list')
        except Exception as e:
            messages.error(request, f'Error deleting expense: {str(e)}')
    
    context = {
        'expense': expense,
    }
    return render(request, 'expenses/expense_confirm_delete.html', context)
