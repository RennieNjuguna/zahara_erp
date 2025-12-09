from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from orders.models import Order
from payments.models import Payment
from expenses.models import Expense
from customers.models import Customer
from customers.models import Customer
from products.models import Product

from django.contrib.auth import login
from .forms import LoginForm

def custom_login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})



def home(request):
    """Home dashboard view with real-time data"""
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # Today's revenue (from orders)
    today_revenue = Order.objects.filter(
        date=today,
        status__in=['paid', 'partial']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Yesterday's revenue for comparison
    yesterday_revenue = Order.objects.filter(
        date=yesterday,
        status__in=['paid', 'partial']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Calculate revenue change percentage
    if yesterday_revenue > 0:
        revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
    else:
        revenue_change = 0 if today_revenue == 0 else 100

    # Today's expenses
    today_expenses = Expense.objects.filter(
        date_incurred=today,
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Yesterday's expenses for comparison
    yesterday_expenses = Expense.objects.filter(
        date_incurred=yesterday,
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate expense change percentage
    if yesterday_expenses > 0:
        expense_change = ((today_expenses - yesterday_expenses) / yesterday_expenses) * 100
    else:
        expense_change = 0 if today_expenses == 0 else 100

    # Unpaid orders (status pending, excluding paid)
    overdue_orders = Order.objects.filter(
        status='pending'
    ).exclude(status='paid')

    overdue_amount = sum(order.outstanding_amount() for order in overdue_orders)

    # Upcoming payments (pending payments)
    upcoming_payments = Payment.objects.filter(status='pending')
    upcoming_amount = upcoming_payments.aggregate(total=Sum('amount'))['total'] or 0

    # Recent orders (last 5)
    recent_orders = Order.objects.select_related('customer').order_by('-date')[:5]

    # Recent transactions (combine orders and payments)
    recent_transactions = []

    # Add recent orders as transactions
    for order in Order.objects.filter(date__gte=today - timedelta(days=7)).order_by('-date')[:10]:
        recent_transactions.append({
            'company': order.customer.name,
            'amount': order.total_amount,
            'currency': order.currency,
            'time': order.date,
            'is_positive': True
        })

    # Add recent payments as transactions
    for payment in Payment.objects.filter(payment_date__gte=today - timedelta(days=7)).order_by('-payment_date')[:10]:
        recent_transactions.append({
            'company': payment.customer.name,
            'amount': payment.amount,
            'currency': payment.currency,
            'time': payment.payment_date,
            'is_positive': False
        })

    # Sort by time and take top 10
    recent_transactions.sort(key=lambda x: x['time'], reverse=True)
    recent_transactions = recent_transactions[:10]

    context = {
        'today_revenue': today_revenue,
        'revenue_change': revenue_change,
        'today_expenses': today_expenses,
        'expense_change': expense_change,
        'overdue_orders': overdue_orders,
        'overdue_amount': overdue_amount,
        'upcoming_payments': upcoming_payments,
        'upcoming_amount': upcoming_amount,
        'recent_orders': recent_orders,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'home.html', context)

def graphs(request):
    """Dedicated graphs dashboard view"""
    # Get data for charts
    customers = Customer.objects.all()
    products = Product.objects.all()

    # Top products by order count - fix the query
    top_products = Order.objects.values('items__product__name').annotate(
        order_count=Count('id')
    ).filter(items__product__name__isnull=False).order_by('-order_count')[:5]

    # Customer orders distribution - fix the query
    customer_orders = Order.objects.values('customer__name').annotate(
        order_count=Count('id')
    ).filter(customer__name__isnull=False).order_by('-order_count')[:10]

    # Monthly revenue for last 12 months
    monthly_revenue = []
    monthly_labels = []

    for i in range(12):
        month_date = timezone.now() - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        month_revenue = Order.objects.filter(
            date__range=[month_start, month_end],
            status__in=['paid', 'partial']
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        monthly_revenue.append(float(month_revenue))
        monthly_labels.append(month_start.strftime('%b %Y'))

    # Reverse to show oldest to newest
    monthly_revenue.reverse()
    monthly_labels.reverse()

    # Expense categories
    expense_categories = Expense.objects.values('category__name').annotate(
        total=Sum('amount')
    ).filter(category__name__isnull=False).order_by('-total')[:8]

    # Convert to list and handle None values
    top_products_list = []
    for item in top_products:
        if item['items__product__name']:
            top_products_list.append({
                'product__name': item['items__product__name'],
                'order_count': item['order_count']
            })

    customer_orders_list = []
    for item in customer_orders:
        if item['customer__name']:
            customer_orders_list.append({
                'customer__name': item['customer__name'],
                'order_count': item['order_count']
            })

    expense_categories_list = []
    for item in expense_categories:
        if item['category__name']:
            expense_categories_list.append({
                'category__name': item['category__name'],
                'total': float(item['total'])
            })

    context = {
        'customers': customers,
        'products': products,
        'top_products': top_products_list,
        'customer_orders': customer_orders_list,
        'monthly_revenue': monthly_revenue,
        'monthly_labels': monthly_labels,
        'expense_categories': expense_categories_list,
    }

    return render(request, 'graphs.html', context)
