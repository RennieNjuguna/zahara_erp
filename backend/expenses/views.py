from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Expense, ExpenseCategory, ExpenseAttachment
from django.http import JsonResponse


def expense_list(request):
    """Display list of all expenses with search and filtering"""
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
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

    if currency_filter:
        expenses = expenses.filter(currency=currency_filter)

    # Get filter options
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    currencies = Expense.CURRENCY_CHOICES

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
        'currency_filter': currency_filter,
        'categories': categories,
        'currencies': currencies,
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
        name = request.POST.get('name')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency')
        category_id = request.POST.get('category')
        reference_number = request.POST.get('reference_number')
        date_incurred = request.POST.get('date_incurred')
        vendor_name = request.POST.get('vendor_name')
        description = request.POST.get('description')
        created_by = request.POST.get('created_by')

        if name and amount and currency and date_incurred:
            try:
                expense = Expense.objects.create(
                    name=name,
                    amount=amount,
                    currency=currency,
                    category_id=category_id if category_id else None,
                    reference_number=reference_number,
                    date_incurred=date_incurred,
                    vendor_name=vendor_name,
                    description=description,
                    created_by=created_by
                )

                # Handle file attachments
                attachments = request.FILES.getlist('attachments')
                for attachment_file in attachments:
                    ExpenseAttachment.objects.create(
                        expense=expense,
                        file=attachment_file,
                        file_type='receipt'  # Default to receipt
                    )

                messages.success(request, f'Expense "{expense.name}" created successfully!')
                return redirect('expenses:expense_detail', expense_id=expense.id)

            except Exception as e:
                messages.error(request, f'Error creating expense: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')

    # Get categories and currencies for the form
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    currencies = Expense.CURRENCY_CHOICES

    context = {
        'categories': categories,
        'currencies': currencies,
    }
    return render(request, 'expenses/expense_form.html', context)


def expense_edit(request, expense_id):
    """Edit an existing expense"""
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency')
        category_id = request.POST.get('category')
        reference_number = request.POST.get('reference_number')
        date_incurred = request.POST.get('date_incurred')
        vendor_name = request.POST.get('vendor_name')
        description = request.POST.get('description')
        created_by = request.POST.get('created_by')

        if name and amount and currency and date_incurred:
            try:
                expense.name = name
                expense.amount = amount
                expense.currency = currency
                expense.category_id = category_id if category_id else None
                expense.reference_number = reference_number
                expense.date_incurred = date_incurred
                expense.vendor_name = vendor_name
                expense.description = description
                expense.created_by = created_by
                expense.save()

                # Handle new file attachments
                attachments = request.FILES.getlist('attachments')
                for attachment_file in attachments:
                    ExpenseAttachment.objects.create(
                        expense=expense,
                        file=attachment_file,
                        file_type='receipt'  # Default to receipt
                    )

                messages.success(request, f'Expense "{expense.name}" updated successfully!')
                return redirect('expenses:expense_detail', expense_id=expense.id)

            except Exception as e:
                messages.error(request, f'Error updating expense: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')

    # Get categories and currencies for the form
    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    currencies = Expense.CURRENCY_CHOICES

    context = {
        'expense': expense,
        'categories': categories,
        'currencies': currencies,
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


# Category Management Views
def category_list(request):
    """Display list of all expense categories"""
    categories = ExpenseCategory.objects.all().order_by('name')

    context = {
        'categories': categories,
    }
    return render(request, 'expenses/category_list.html', context)


def category_create(request):
    """Create a new expense category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        color = request.POST.get('color', '#007bff')

        if name:
            try:
                category = ExpenseCategory.objects.create(
                    name=name,
                    description=description,
                    color=color
                )

                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'category_id': category.id,
                        'category_name': category.name,
                        'message': f'Category "{category.name}" created successfully!'
                    })
                else:
                    messages.success(request, f'Category "{category.name}" created successfully!')
                    return redirect('expenses:category_list')

            except Exception as e:
                error_msg = f'Error creating category: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })
                else:
                    messages.error(request, error_msg)
        else:
            error_msg = 'Category name is required.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)

    context = {}
    return render(request, 'expenses/category_form.html', context)


def category_edit(request, category_id):
    """Edit an existing expense category"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        color = request.POST.get('color')
        is_active = request.POST.get('is_active') == 'on'

        if name:
            try:
                category.name = name
                category.description = description
                category.color = color
                category.is_active = is_active
                category.save()
                messages.success(request, f'Category "{category.name}" updated successfully!')
                return redirect('expenses:category_list')
            except Exception as e:
                messages.error(request, f'Error updating category: {str(e)}')
        else:
            messages.error(request, 'Category name is required.')

    context = {
        'category': category,
    }
    return render(request, 'expenses/category_form.html', context)


def category_delete(request, category_id):
    """Delete an expense category"""
    category = get_object_or_404(ExpenseCategory, id=category_id)

    if request.method == 'POST':
        try:
            category_name = category.name
            category.delete()
            messages.success(request, f'Category "{category_name}" deleted successfully!')
            return redirect('expenses:category_list')
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')

    context = {
        'category': category,
    }
    return render(request, 'expenses/category_confirm_delete.html', context)
