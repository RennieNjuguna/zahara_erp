from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from orders.models import Order
from payments.models import Payment, Expense
from customers.models import Customer
from products.models import Product


def home(request):
    """Home dashboard view with real data from database"""

    # Get current date and time
    now = timezone.now()
    today = now.date()

    # Calculate date ranges
    yesterday = today - timedelta(days=1)
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    # Today's revenue (orders created today)
    today_revenue = Order.objects.filter(
        date=today
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')

    # Today's expenses
    today_expenses = Expense.objects.filter(
        date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Overdue orders (orders with due date passed and not fully paid)
    overdue_orders = Order.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    ).order_by('due_date')

    overdue_amount = overdue_orders.aggregate(
        total=Sum('outstanding_amount')
    )['total'] or Decimal('0.00')

    # Upcoming payments (payments scheduled for today and tomorrow)
    upcoming_payments = Payment.objects.filter(
        payment_date__in=[today, today + timedelta(days=1)],
        status='pending'
    ).order_by('payment_date')

    upcoming_amount = upcoming_payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Recent orders (last 5 orders)
    recent_orders = Order.objects.select_related('customer').order_by('-date')[:5]

    # Recent transactions (payments and expenses)
    recent_payments = Payment.objects.select_related('customer').filter(
        payment_date__gte=today - timedelta(days=7)
    ).order_by('-payment_date')[:5]

    recent_expenses = Expense.objects.filter(
        date__gte=today - timedelta(days=7)
    ).order_by('-date')[:5]

    # Combine and sort recent transactions
    recent_transactions = []

    for payment in recent_payments:
        recent_transactions.append({
            'type': 'payment',
            'company': payment.customer.name,
            'amount': payment.amount,
            'time': payment.payment_date,
            'is_positive': True,
            'currency': payment.currency
        })

    for expense in recent_expenses:
        recent_transactions.append({
            'type': 'expense',
            'company': expense.category.name if expense.category else 'Expense',
            'amount': expense.amount,
            'time': expense.date,
            'is_positive': False,
            'currency': expense.currency
        })

    # Sort by time (most recent first)
    recent_transactions.sort(key=lambda x: x['time'], reverse=True)
    recent_transactions = recent_transactions[:5]

    # Calculate percentage changes (simplified - comparing today vs yesterday)
    yesterday_revenue = Order.objects.filter(
        date=yesterday
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')

    yesterday_expenses = Expense.objects.filter(
        date=yesterday
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Calculate percentage changes
    revenue_change = 0
    if yesterday_revenue > 0:
        revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100

    expense_change = 0
    if yesterday_expenses > 0:
        expense_change = ((today_expenses - yesterday_expenses) / yesterday_expenses) * 100

    context = {
        'today_revenue': today_revenue,
        'today_expenses': today_expenses,
        'overdue_orders': overdue_orders,
        'overdue_amount': overdue_amount,
        'upcoming_payments': upcoming_payments,
        'upcoming_amount': upcoming_amount,
        'recent_orders': recent_orders,
        'recent_transactions': recent_transactions,
        'revenue_change': revenue_change,
        'expense_change': expense_change,
        'last_updated': now,
    }

    return render(request, 'home.html', context)
