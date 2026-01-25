from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Customer, Branch
from orders.models import Order
from payments.models import CustomerBalance
from payments.models import Payment
from django.db.models import Sum


def customer_list(request):
    """Display list of all customers with search and pagination"""
    search_query = request.GET.get('search', '')
    currency_filter = request.GET.get('currency', '')

    customers = Customer.objects.all().order_by('name')

    # Apply search filter
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(short_code__icontains=search_query)
        )

    # Apply currency filter
    if currency_filter:
        customers = customers.filter(preferred_currency=currency_filter)

    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get currency choices for filter
    currency_choices = Customer.CURRENCY_CHOICES

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'currency_filter': currency_filter,
        'currency_choices': currency_choices,
        'total_customers': customers.count(),
    }
    return render(request, 'customers/customer_list.html', context)


def customer_detail(request, customer_id):
    """Display detailed information about a specific customer"""
    customer = get_object_or_404(Customer, id=customer_id)

    # Get customer statistics
    stats = customer.get_order_statistics()

    # Get recent orders
    recent_orders = customer.orders.all().order_by('-date')[:10]

    # Get customer balance (this is our single source of truth)
    try:
        balance = CustomerBalance.objects.get(customer=customer)
        current_balance = balance.current_balance
    except CustomerBalance.DoesNotExist:
        current_balance = 0

    # Calculate total payments received
    total_payments = Payment.objects.filter(
        customer=customer,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Add total payments to stats
    stats['total_payments'] = total_payments

    # Calculate unallocated amount
    unallocated_amount = customer.unallocated_payments()

    # Get branches
    branches = customer.branches.all()

    context = {
        'customer': customer,
        'stats': stats,
        'recent_orders': recent_orders,
        'current_balance': current_balance,
        'unallocated_amount': unallocated_amount,
        'branches': branches,
    }
    return render(request, 'customers/customer_detail.html', context)


def customer_create(request):
    """Create a new customer"""
    if request.method == 'POST':
        name = request.POST.get('name')
        short_code = request.POST.get('short_code')
        preferred_currency = request.POST.get('preferred_currency')
        invoice_code_preference = request.POST.get('invoice_code_preference', 'branch')
        email = request.POST.get('email')

        if name and short_code and preferred_currency:
            try:
                customer = Customer.objects.create(
                    name=name,
                    short_code=short_code,
                    preferred_currency=preferred_currency,
                    invoice_code_preference=invoice_code_preference,
                    email=email  # Save email
                )
                messages.success(request, f'Customer "{customer.name}" created successfully!')
                return redirect('customers:customer_detail', customer_id=customer.id)
            except Exception as e:
                messages.error(request, f'Error creating customer: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')

    context = {
        'currency_choices': Customer.CURRENCY_CHOICES,
    }
    return render(request, 'customers/customer_form.html', context)


def customer_edit(request, customer_id):
    """Edit an existing customer"""
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        short_code = request.POST.get('short_code')
        preferred_currency = request.POST.get('preferred_currency')
        invoice_code_preference = request.POST.get('invoice_code_preference', 'branch')
        email = request.POST.get('email')

        if name and short_code and preferred_currency:
            try:
                customer.name = name
                customer.short_code = short_code
                customer.preferred_currency = preferred_currency
                customer.invoice_code_preference = invoice_code_preference
                customer.email = email  # Update email
                customer.save()
                messages.success(request, f'Customer "{customer.name}" updated successfully!')
                return redirect('customers:customer_detail', customer_id=customer.id)
            except Exception as e:
                messages.error(request, f'Error updating customer: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')

    context = {
        'customer': customer,
        'currency_choices': Customer.CURRENCY_CHOICES,
    }
    return render(request, 'customers/customer_form.html', context)


def customer_delete(request, customer_id):
    """Delete a customer"""
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        try:
            customer_name = customer.name
            customer.delete()
            messages.success(request, f'Customer "{customer_name}" deleted successfully!')
            return redirect('customers:customer_list')
        except Exception as e:
            messages.error(request, f'Error deleting customer: {str(e)}')

    context = {
        'customer': customer,
    }
    return render(request, 'customers/customer_confirm_delete.html', context)


def branch_create(request, customer_id):
    """Create a new branch for a customer"""
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        short_code = request.POST.get('short_code')

        if name and short_code:
            try:
                branch = Branch.objects.create(
                    customer=customer,
                    name=name,
                    short_code=short_code
                )
                messages.success(request, f'Branch "{branch.name}" created successfully!')
                return redirect('customers:customer_detail', customer_id=customer.id)
            except Exception as e:
                messages.error(request, f'Error creating branch: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')

    context = {
        'customer': customer,
    }
    return render(request, 'customers/branch_form.html', context)


def branch_edit(request, branch_id):
    """Edit an existing branch"""
    branch = get_object_or_404(Branch, id=branch_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        short_code = request.POST.get('short_code')

        if name and short_code:
            try:
                branch.name = name
                branch.short_code = short_code
                branch.save()
                messages.success(request, f'Branch "{branch.name}" updated successfully!')
                return redirect('customers:customer_detail', customer_id=branch.customer.id)
            except Exception as e:
                messages.error(request, f'Error updating branch: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')

    context = {
        'branch': branch,
    }
    return render(request, 'customers/branch_form.html', context)


def branch_delete(request, branch_id):
    """Delete a branch"""
    branch = get_object_or_404(Branch, id=branch_id)
    customer_id = branch.customer.id

    if request.method == 'POST':
        try:
            branch_name = branch.name
            branch.delete()
            messages.success(request, f'Branch "{branch_name}" deleted successfully!')
            return redirect('customers:customer_detail', customer_id=customer_id)
        except Exception as e:
            messages.error(request, f'Error deleting branch: {str(e)}')

    context = {
        'branch': branch,
    }
    return render(request, 'customers/branch_confirm_delete.html', context)


def quick_branch_create(request):
    """Create a new branch quickly from the customer list page"""
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        name = request.POST.get('name')
        short_code = request.POST.get('short_code')

        if customer_id and name and short_code:
            try:
                customer = Customer.objects.get(id=customer_id)
                branch = Branch.objects.create(
                    customer=customer,
                    name=name,
                    short_code=short_code
                )
                messages.success(request, f'Branch "{branch.name}" created successfully for {customer.name}!')
                return redirect('customers:customer_list')
            except Customer.DoesNotExist:
                messages.error(request, 'Customer not found.')
            except Exception as e:
                messages.error(request, f'Error creating branch: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')

    return redirect('customers:customer_list')
