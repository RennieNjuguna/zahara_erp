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

@login_required
def update_rates(request):
    """View to trigger exchange rate update manually"""
    from payments.utils import fetch_and_update_rates
    from django.contrib import messages
    
    success, msg = fetch_and_update_rates()
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
        
    return redirect('home')




def home(request):
    """Home dashboard view with monthly metrics and unified transaction feed"""
    from orders.models import OrderItem, Order
    from payments.models import Payment
    from expenses.models import Expense
    from invoices.models import CreditNote
    
    # Date range for current month
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    # End of month computation
    if start_of_month.month == 12:
        end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1) - timezone.timedelta(days=1)
    else:
        end_of_month = start_of_month.replace(month=start_of_month.month + 1, day=1) - timezone.timedelta(days=1)

    # Helper function for currency conversion
    from payments.models import ExchangeRate
    
    # Cache rates
    rates = {}
    for rate in ExchangeRate.objects.all():
        rates[rate.currency] = rate.rate
    
    def convert_to_ksh(amount, currency):
        if not amount: return Decimal('0.00')
        if currency == 'KSH': return amount
        rate = rates.get(currency, Decimal('1.0'))
        return amount * rate

    # 1. Month Total Sales (Total Order Value Converted)
    month_orders = Order.objects.filter(
        date__gte=start_of_month,
        date__lte=end_of_month
    )
    month_sales = sum(convert_to_ksh(o.total_amount, o.currency) for o in month_orders)

    # 2. Month Total Revenue (Payments Completed Converted)
    month_payments_qs = Payment.objects.filter(
        payment_date__gte=start_of_month,
        payment_date__lte=end_of_month,
        status='completed'
    )
    month_revenue = sum(convert_to_ksh(p.amount, p.currency) for p in month_payments_qs)

    # 3. Month Total Expenses (Converted)
    month_expenses_qs = Expense.objects.filter(
        date_incurred__gte=start_of_month,
        date_incurred__lte=end_of_month
    )
    month_expenses = sum(convert_to_ksh(e.amount, e.currency) for e in month_expenses_qs)

    # 4. Order Status Counts
    paid_orders_count = Order.objects.filter(
        date__gte=start_of_month,
        date__lte=end_of_month,
        status='paid'
    ).count()

    unpaid_orders_count = Order.objects.filter(
        date__gte=start_of_month,
        date__lte=end_of_month,
        status='pending'
    ).count()

    # 5. Total Credits (Converted)
    month_credits_qs = CreditNote.objects.filter(
        created_at__date__gte=start_of_month,
        created_at__date__lte=end_of_month,
        status='approved'
    )
    month_credits = sum(convert_to_ksh(c.total_amount, c.currency) for c in month_credits_qs)

    # 6. Most Ordered Product
    top_product_data = OrderItem.objects.filter(
        order__date__gte=start_of_month,
        order__date__lte=end_of_month
    ).values('product__name').annotate(
        total_qty=Sum('stems')
    ).order_by('-total_qty').first()
    
    top_product = top_product_data['product__name'] if top_product_data else "N/A"
    top_product_qty = top_product_data['total_qty'] if top_product_data else 0

    # 7. Highest Ordering Customer (Converted Amount)
    # Note: Complex aggregation with conversion in DB is hard, so we iterate
    # This might be slow if many orders, but for dashboard valid for now
    customer_spend = {}
    for order in month_orders:
        name = order.customer.name
        val = convert_to_ksh(order.total_amount, order.currency)
        customer_spend[name] = customer_spend.get(name, Decimal('0')) + val
    
    if customer_spend:
        top_customer = max(customer_spend, key=customer_spend.get)
        top_customer_amount = customer_spend[top_customer]
    else:
        top_customer = "N/A"
        top_customer_amount = 0

    # Recent Orders (Limit 5)
    recent_orders = Order.objects.select_related('customer').order_by('-date')[:5]

    # Unified Transaction Feed (Limit 5)
    # Payments
    recent_payments = Payment.objects.filter(status='completed').order_by('-payment_date')[:5]
    payment_list = [{
        'type': 'payment',
        'date': p.payment_date,
        'description': f"Payment from {p.customer.name}",
        'amount': p.amount,
        'currency': p.currency,
        'reference': p.reference_number
    } for p in recent_payments]

    # Expenses
    recent_expenses = Expense.objects.all().order_by('-date_incurred')[:5]
    expense_list = [{
        'type': 'expense',
        'date': e.date_incurred,
        'description': f"{e.category.name if e.category else 'Expense'}: {e.name}",
        'amount': e.amount,
        'currency': e.currency,
        'reference': e.reference_number
    } for e in recent_expenses]

    # Combine and Sort
    recent_transactions = sorted(payment_list + expense_list, key=lambda x: x['date'], reverse=True)[:5]

    context = {
        'current_month': start_of_month.strftime('%B %Y'),
        'metrics': {
            'total_sales': month_sales,
            'revenue': month_revenue,
            'expenses': month_expenses,
            'paid_orders': paid_orders_count,
            'unpaid_orders': unpaid_orders_count,
            'credits': month_credits,
            'top_product': top_product,
            'top_product_qty': top_product_qty,
            'top_customer': top_customer,
            'top_customer_amount': top_customer_amount,
        },
        'recent_transactions': recent_transactions,
        'recent_orders': recent_orders,
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
