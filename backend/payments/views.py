from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import json

from .models import (
    Payment, PaymentType, PaymentAllocation, CustomerBalance,
    AccountStatement, PaymentLog
)
from customers.models import Customer
from orders.models import Order
from invoices.models import CreditNote


@login_required
def payment_dashboard(request):
    """Main payment dashboard"""
    # Get summary statistics
    total_payments = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    total_outstanding = Customer.objects.aggregate(
        total=Sum('outstanding_amount')
    )['total'] or Decimal('0.00')

    recent_payments = Payment.objects.filter(
        status='completed'
    ).order_by('-payment_date')[:10]

    customers_with_balances = CustomerBalance.objects.filter(
        current_balance__gt=0
    ).order_by('-current_balance')[:10]

    context = {
        'total_payments': total_payments,
        'total_outstanding': total_outstanding,
        'recent_payments': recent_payments,
        'customers_with_balances': customers_with_balances,
    }

    return render(request, 'payments/dashboard.html', context)


@login_required
def payment_list(request):
    """List all payments with filtering and search"""
    payments = Payment.objects.all()

    # Filtering
    customer_id = request.GET.get('customer')
    if customer_id:
        payments = payments.filter(customer_id=customer_id)

    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)

    payment_method = request.GET.get('payment_method')
    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    date_from = request.GET.get('date_from')
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    # Search
    search = request.GET.get('search')
    if search:
        payments = payments.filter(
            Q(customer__name__icontains=search) |
            Q(reference_number__icontains=search) |
            Q(notes__icontains=search)
        )

    # Pagination
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    customers = Customer.objects.all().order_by('name')
    payment_types = PaymentType.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'customers': customers,
        'payment_types': payment_types,
        'filters': request.GET,
    }

    return render(request, 'payments/payment_list.html', context)


@login_required
def payment_detail(request, payment_id):
    """Detailed view of a payment"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    allocations = payment.allocations.all()

    # Get outstanding orders for this customer
    outstanding_orders = payment.customer.orders.filter(
        total_amount__gt=0
    ).order_by('date')

    context = {
        'payment': payment,
        'allocations': allocations,
        'outstanding_orders': outstanding_orders,
    }

    return render(request, 'payments/payment_detail.html', context)


@login_required
def payment_create(request):
    """Create a new payment"""
    if request.method == 'POST':
        # Handle payment creation
        try:
            customer_id = request.POST.get('customer')
            payment_type_id = request.POST.get('payment_type')
            amount = request.POST.get('amount')
            payment_method = request.POST.get('payment_method')
            payment_date = request.POST.get('payment_date')
            reference_number = request.POST.get('reference_number')
            notes = request.POST.get('notes')

            customer = Customer.objects.get(id=customer_id)
            payment_type = PaymentType.objects.get(id=payment_type_id)

            payment = Payment.objects.create(
                customer=customer,
                payment_type=payment_type,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                reference_number=reference_number,
                notes=notes,
                currency=customer.preferred_currency
            )

            # Log the payment creation
            PaymentLog.objects.create(
                action='payment_created',
                user=request.user.username,
                payment=payment,
                customer=customer,
                            details=json.dumps({
                'amount': str(amount),
                'payment_method': payment_method,
                'reference_number': reference_number
            })
            )

            messages.success(request, f'Payment created successfully: {payment}')
            return redirect('payment_detail', payment_id=payment.payment_id)

        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')

    # GET request - show form
    customers = Customer.objects.all().order_by('name')
    payment_types = PaymentType.objects.filter(is_active=True)

    context = {
        'customers': customers,
        'payment_types': payment_types,
    }

    return render(request, 'payments/payment_form.html', context)


@login_required
def payment_edit(request, payment_id):
    """Edit an existing payment"""
    payment = get_object_or_404(Payment, payment_id=payment_id)

    if request.method == 'POST':
        # Handle payment update
        try:
            payment.customer_id = request.POST.get('customer')
            payment.payment_type_id = request.POST.get('payment_type')
            payment.amount = request.POST.get('amount')
            payment.payment_method = request.POST.get('payment_method')
            payment.payment_date = request.POST.get('payment_date')
            payment.reference_number = request.POST.get('reference_number')
            payment.notes = request.POST.get('notes')
            payment.status = request.POST.get('status')

            payment.save()

            # Log the payment update
            PaymentLog.objects.create(
                action='payment_updated',
                user=request.user.username,
                payment=payment,
                customer=payment.customer,
                details=json.dumps({'updated_fields': list(request.POST.keys())})
            )

            messages.success(request, f'Payment updated successfully: {payment}')
            return redirect('payment_detail', payment_id=payment.payment_id)

        except Exception as e:
            messages.error(request, f'Error updating payment: {str(e)}')

    # GET request - show form
    customers = Customer.objects.all().order_by('name')
    payment_types = PaymentType.objects.filter(is_active=True)

    context = {
        'payment': payment,
        'customers': customers,
        'payment_types': payment_types,
    }

    return render(request, 'payments/payment_form.html', context)


@login_required
def customer_balance_list(request):
    """List all customer balances with enhanced statistics"""
    # Get all customers with their order statistics
    customers_with_stats = []

    for customer in Customer.objects.all():
        # Get or create balance
        balance, created = CustomerBalance.objects.get_or_create(
            customer=customer,
            defaults={'currency': customer.preferred_currency}
        )

        if created:
            balance.recalculate_balance()

        # Get order statistics using the new method
        stats = customer.get_order_statistics()

        customers_with_stats.append({
            'customer': customer,
            'balance': balance,
            'total_orders': stats['total_orders'],
            'total_sales': stats['total_sales'],
            'pending_orders': stats['pending_orders'],
            'claimed_orders': stats['claimed_orders'],
            'paid_orders': stats['paid_orders'],
        })

    # Sort by current balance (descending)
    customers_with_stats.sort(key=lambda x: x['balance'].current_balance, reverse=True)

    # Filtering
    currency = request.GET.get('currency')
    if currency:
        customers_with_stats = [c for c in customers_with_stats if c['balance'].currency == currency]

    # Search
    search = request.GET.get('search')
    if search:
        customers_with_stats = [c for c in customers_with_stats if search.lower() in c['customer'].name.lower()]

    # Pagination
    paginator = Paginator(customers_with_stats, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filters': request.GET,
    }

    return render(request, 'payments/customer_balance_list.html', context)


@login_required
def customer_balance_detail(request, customer_id):
    """Detailed view of customer balance and payment history"""
    customer = get_object_or_404(Customer, id=customer_id)

    # Get or create balance
    balance, created = CustomerBalance.objects.get_or_create(
        customer=customer,
        defaults={'currency': customer.preferred_currency}
    )

    if created:
        balance.recalculate_balance()

    # Get payment history
    payments = Payment.objects.filter(
        customer=customer
    ).order_by('-payment_date')

    # Get outstanding orders
    outstanding_orders = customer.orders.filter(
        total_amount__gt=0
    ).order_by('date')

    # Get recent account statements
    statements = customer.account_statements.all().order_by('-statement_date')[:5]

    context = {
        'customer': customer,
        'balance': balance,
        'payments': payments,
        'outstanding_orders': outstanding_orders,
        'statements': statements,
    }

    return render(request, 'payments/customer_balance_detail.html', context)


@login_required
def account_statement_list(request):
    """List all account statements"""
    statements = AccountStatement.objects.all().order_by('-statement_date')

    # Filtering
    customer_id = request.GET.get('customer')
    if customer_id:
        statements = statements.filter(customer_id=customer_id)

    year = request.GET.get('year')
    if year:
        statements = statements.filter(statement_date__year=year)

    # Search
    search = request.GET.get('search')
    if search:
        statements = statements.filter(customer__name__icontains=search)

    # Pagination
    paginator = Paginator(statements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    customers = Customer.objects.all().order_by('name')
    years = AccountStatement.objects.dates('statement_date', 'year')

    context = {
        'page_obj': page_obj,
        'customers': customers,
        'years': years,
        'filters': request.GET,
    }

    return render(request, 'payments/account_statement_list.html', context)


@login_required
def account_statement_detail(request, statement_id):
    """Detailed view of an account statement"""
    statement = get_object_or_404(AccountStatement, id=statement_id)

    # Generate statement data if not already done
    if statement.opening_balance == 0 and statement.closing_balance == 0:
        statement_data = statement.generate_statement_data()
    else:
        statement_data = {
            'orders': statement.customer.orders.filter(
                date__gte=statement.start_date,
                date__lte=statement.end_date
            ),
            'credits': CreditNote.objects.filter(
                order__customer=statement.customer,
                created_at__date__gte=statement.start_date,
                created_at__date__lte=statement.end_date
            ),
            'payments': Payment.objects.filter(
                customer=statement.customer,
                payment_date__gte=statement.start_date,
                payment_date__lte=statement.end_date,
                status='completed'
            ),
        }

    context = {
        'statement': statement,
        'statement_data': statement_data,
    }

    return render(request, 'payments/account_statement_detail.html', context)


@login_required
def generate_account_statement(request, customer_id):
    """Generate a new account statement for a customer"""
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == 'POST':
        try:
            statement_date = request.POST.get('statement_date')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # Check if statement already exists for this month
            existing_statement = AccountStatement.objects.filter(
                customer=customer,
                statement_date=statement_date
            ).first()

            if existing_statement:
                messages.warning(request, 'Statement for this month already exists.')
                return redirect('account_statement_detail', statement_id=existing_statement.id)

            # Create new statement
            statement = AccountStatement.objects.create(
                customer=customer,
                statement_date=statement_date,
                start_date=start_date,
                end_date=end_date,
                generated_by=request.user.username
            )

            # Generate statement data
            statement.generate_statement_data()

            # Log statement generation
            PaymentLog.objects.create(
                action='statement_generated',
                user=request.user.username,
                customer=customer,
                details=json.dumps({
                    'statement_id': statement.id,
                    'start_date': start_date,
                    'end_date': end_date
                })
            )

            messages.success(request, f'Account statement generated successfully.')
            return redirect('account_statement_detail', statement_id=statement.id)

        except Exception as e:
            messages.error(request, f'Error generating statement: {str(e)}')

    # GET request - show form
    context = {
        'customer': customer,
    }

    return render(request, 'payments/generate_statement_form.html', context)


@login_required
@require_http_methods(["POST"])
def allocate_payment(request, payment_id):
    """Allocate payment to orders via AJAX"""
    try:
        payment = get_object_or_404(Payment, payment_id=payment_id)
        data = json.loads(request.body)
        allocations = data.get('allocations', [])

        # Validate allocations
        total_allocation = sum(item['amount'] for item in allocations)
        if total_allocation > payment.unallocated_amount:
            return JsonResponse({
                'success': False,
                'error': 'Total allocation amount exceeds unallocated payment amount'
            }, status=400)

        # Create allocations
        created_allocations = []
        for item in allocations:
            order = Order.objects.get(id=item['order_id'])
            allocation = PaymentAllocation.objects.create(
                payment=payment,
                order=order,
                amount=item['amount']
            )
            created_allocations.append({
                'id': allocation.id,
                'order_invoice': order.invoice_code,
                'amount': str(allocation.amount)
            })

        # Log allocation
        PaymentLog.objects.create(
            action='allocation_created',
            user=request.user.username,
            payment=payment,
            customer=payment.customer,
            details=json.dumps({'allocations': created_allocations})
        )

        return JsonResponse({
            'success': True,
            'allocations': created_allocations,
            'remaining_amount': str(payment.unallocated_amount)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def recalculate_balance(request, customer_id):
    """Recalculate customer balance via AJAX"""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        balance, created = CustomerBalance.objects.get_or_create(
            customer=customer,
            defaults={'currency': customer.preferred_currency}
        )

        new_balance = balance.recalculate_balance()

        # Log balance recalculation
        PaymentLog.objects.create(
            action='balance_recalculated',
            user=request.user.username,
            customer=customer,
            details=json.dumps({'new_balance': str(new_balance)})
        )

        return JsonResponse({
            'success': True,
            'balance': str(new_balance),
            'currency': balance.currency
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def payment_analytics(request):
    """Payment analytics and reporting"""
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - relativedelta(months=6)

    # Payment trends
    payment_trends = Payment.objects.filter(
        payment_date__gte=start_date,
        status='completed'
    ).values('payment_date').annotate(
        total=Sum('amount')
    ).order_by('payment_date')

    # Payment methods breakdown
    payment_methods = Payment.objects.filter(
        payment_date__gte=start_date,
        status='completed'
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )

    # Top customers by payment amount
    top_customers = Payment.objects.filter(
        payment_date__gte=start_date,
        status='completed'
    ).values('customer__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]

    context = {
        'payment_trends': payment_trends,
        'payment_methods': payment_methods,
        'top_customers': top_customers,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'payments/analytics.html', context)


# API endpoints for AJAX calls
@csrf_exempt
@require_http_methods(["GET"])
def get_outstanding_orders(request, customer_id):
    """Get outstanding orders for a customer"""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        orders = customer.orders.filter(
            total_amount__gt=0
        ).values('id', 'invoice_code', 'date', 'total_amount')

        # Calculate outstanding amount for each order
        for order in orders:
            order_obj = Order.objects.get(id=order['id'])
            order['outstanding_amount'] = str(order_obj.outstanding_amount())

        return JsonResponse({'orders': list(orders)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_customer_balance(request, customer_id):
    """Get current balance for a customer"""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        balance = customer.current_balance()

        return JsonResponse({
            'balance': str(balance),
            'currency': customer.preferred_currency
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
