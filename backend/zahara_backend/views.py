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
    from core.models import UserPreference
    
    # Determine target currency
    target_currency = 'KES'
    if request.user.is_authenticated:
        try:
            target_currency = request.user.preferences.currency
        except (UserPreference.DoesNotExist, AttributeError):
            pass
            
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
    
    def convert_currency(amount, from_currency, to_currency):
        if not amount: return Decimal('0.00')
        if from_currency == to_currency: return amount
        
        # Convert to KSH first (base)
        rate_to_ksh = rates.get(from_currency, Decimal('1.0'))
        amount_in_ksh = amount * rate_to_ksh
        
        # Then convert from KSH to target
        if to_currency == 'KSH':
            return amount_in_ksh
            
        rate_from_ksh = rates.get(to_currency, Decimal('1.0'))
        # If rate is X KSH per 1 Unit, then 1 KSH = 1/X Units
        # Avoid division by zero
        if rate_from_ksh == 0: return amount_in_ksh
        return amount_in_ksh / rate_from_ksh

    # 1. Month Total Sales (Total Order Value Converted)
    month_orders = Order.objects.filter(
        date__gte=start_of_month,
        date__lte=end_of_month
    )
    month_sales = sum(convert_currency(o.total_amount, o.currency, target_currency) for o in month_orders)

    # 2. Month Total Revenue (Payments Completed Converted)
    month_payments_qs = Payment.objects.filter(
        payment_date__gte=start_of_month,
        payment_date__lte=end_of_month,
        status='completed'
    )
    month_revenue = sum(convert_currency(p.amount, p.currency, target_currency) for p in month_payments_qs)

    # 3. Month Total Expenses (Converted)
    month_expenses_qs = Expense.objects.filter(
        date_incurred__gte=start_of_month,
        date_incurred__lte=end_of_month
    )
    month_expenses = sum(convert_currency(e.amount, e.currency, target_currency) for e in month_expenses_qs)

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
    month_credits = sum(convert_currency(c.total_amount, c.currency, target_currency) for c in month_credits_qs)

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
    customer_spend = {}
    for order in month_orders:
        name = order.customer.name
        val = convert_currency(order.total_amount, order.currency, target_currency)
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
        'currency_label': target_currency, # Pass currency label to template
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
    from orders.models import OrderItem
    from payments.models import Payment
    
    # Get filter params
    customer_id = request.GET.get('customer')
    product_id = request.GET.get('product')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    # Base Order QuerySet
    orders = Order.objects.filter(status__in=['paid', 'partial'])

    # Apply Filters
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    if date_start:
        orders = orders.filter(date__gte=date_start)
    if date_end:
        orders = orders.filter(date__lte=date_end)
    
    # Product filter works effectively on the aggregations below or base set
    # If filtering by product, we heavily restrict the "Orders" base.
    # However, for Revenue charts, usually we want total order value. 
    # If a user filters by product, they likely want to see revenue contributed BY that product?
    # Or just orders containing that product?
    # Standard approach: Filter orders containing the product.
    if product_id:
        orders = orders.filter(items__product_id=product_id).distinct()

    # Get Aggregates based on FILTERED orders
    
    # 1. Top products (in selected range/customer)
    # We re-query OrderItems for these orders
    top_products_qs = OrderItem.objects.filter(order__in=orders)
    if product_id:
        top_products_qs = top_products_qs.filter(product_id=product_id)
        
    top_products = top_products_qs.values('product__name').annotate(
        order_count=Count('order', distinct=True), # Count unique orders
        total_qty=Sum('stems')
    ).order_by('-total_qty')[:5]

    # 2. Customer orders distribution (in selected range)
    # If specific customer selected, this just shows that one customer
    customer_orders = orders.values('customer__name').annotate(
        order_count=Count('id'),
        total_val=Sum('total_amount')
    ).order_by('-total_val')[:10]

    # 3. Monthly revenue
    # If date range is small, this might just show a few months.
    # We'll stick to the "Last 12 Months" logic BUT intersecting with the filtered set.
    monthly_revenue = []
    monthly_labels = []
    
    # Determine range to iterate
    # Default: Last 12 months. If Start/End provided, iterate inclusive months.
    if date_start and date_end:
        try:
            start_date = datetime.strptime(date_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_end, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().date() - timedelta(days=365)
            end_date = timezone.now().date()
    else:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)

    # Allow max 12 data points for readability, or iterate months in range
    # Simplification: Iterate last 12 months window, and filtered orders will naturally report 0 if outside range.
    
    for i in range(12):
        month_date = timezone.now() - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Revenue logic checks against 'orders' queryset
        month_rev = orders.filter(
            date__range=[month_start, month_end]
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        monthly_revenue.append(float(month_rev))
        monthly_labels.append(month_start.strftime('%b %Y'))

    monthly_revenue.reverse()
    monthly_labels.reverse()

    # 4. Expense categories
    # Expenses usually don't link to 'Orders' directly unless cost of goods. 
    # But usually Analytics filters (Customer/Product) don't apply to Expenses well.
    # We will ONLY apply Date filters to Expenses.
    expenses = Expense.objects.all()
    if date_start:
        expenses = expenses.filter(date_incurred__gte=date_start)
    if date_end:
        expenses = expenses.filter(date_incurred__lte=date_end)
        
    expense_categories = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).filter(category__name__isnull=False).order_by('-total')[:8]

    # Serialization
    top_products_list = list(top_products)
    customer_orders_list = list(customer_orders)
    expense_categories_list = list(expense_categories)
    
    # Cast decimals to float for JSON
    for item in customer_orders_list: 
        item['total_val'] = float(item['total_val'] if item['total_val'] else 0)
    for item in expense_categories_list:
        item['total'] = float(item['total'] if item['total'] else 0)

    # --- Advanced Analytics ---

    # 5. Customer-Product Mix (Stacked Bar)
    # Top 10 Customers x Top 5 Products quantity
    # Structure: Labels = Customers, Datasets = Products
    cust_prod_mix = OrderItem.objects.filter(order__in=orders).values(
        'order__customer__name', 'product__name'
    ).annotate(total_qty=Sum('stems')).order_by('-total_qty')
    
    # Process into structured data for Chart.js
    cp_data = {}
    all_products = set()
    for entry in cust_prod_mix:
        c_name = entry['order__customer__name']
        p_name = entry['product__name']
        qty = entry['total_qty']
        
        if c_name not in cp_data: cp_data[c_name] = {}
        cp_data[c_name][p_name] = qty
        all_products.add(p_name)
        
    # Limit to top 10 customers by total volume
    sorted_customers = sorted(cp_data.keys(), key=lambda x: sum(cp_data[x].values()), reverse=True)[:10]
    # Limit to top 5 products overall
    # (Simplified: just take top 5 found across these customers)
    top_5_products = list(all_products)[:5] # Ideally sort by global volume, but set order is arbitrary.
    # accurate sorting of products:
    prod_volumes = {}
    for c in cp_data:
        for p, q in cp_data[c].items():
            prod_volumes[p] = prod_volumes.get(p, 0) + q
    top_5_products = sorted(prod_volumes.keys(), key=lambda x: prod_volumes[x], reverse=True)[:5]

    cp_mix_data = {
        'labels': sorted_customers,
        'datasets': []
    }
    for prod in top_5_products:
        data_points = [cp_data[cust].get(prod, 0) for cust in sorted_customers]
        cp_mix_data['datasets'].append({'label': prod, 'data': data_points})

    # 6. Daily Sales Trend (Line)
    # Last 30 days or selected range
    daily_sales = []
    daily_labels = []
    
    if date_start and date_end:
        # Use selected range, up to reasonable limit (e.g. 60 days) to avoid overcrowding
        d_start = datetime.strptime(date_start, '%Y-%m-%d').date()
        d_end = datetime.strptime(date_end, '%Y-%m-%d').date()
        delta = (d_end - d_start).days
    else:
        d_end = timezone.now().date()
        d_start = d_end - timedelta(days=30)
        delta = 30
        
    # Iterate days
    current_d = d_start
    while current_d <= d_end:
        day_val = orders.filter(date=current_d).aggregate(t=Sum('total_amount'))['t'] or 0
        daily_sales.append(float(day_val))
        daily_labels.append(current_d.strftime('%b %d'))
        current_d += timedelta(days=1)

    # 7. Order Status Distribution (Pie)
    # We want Paid vs Pending vs Claim. 'orders' QS is filtered to paid/partial usually, 
    # but let's query the base objects for status distribution relative to the filters (Cust/Date)
    # Re-apply filters to a fresh Order QuerySet that INCLUDES all statuses
    status_qs = Order.objects.all()
    if customer_id: status_qs = status_qs.filter(customer_id=customer_id)
    if date_start: status_qs = status_qs.filter(date__gte=date_start)
    if date_end: status_qs = status_qs.filter(date__lte=date_end)
    if product_id: status_qs = status_qs.filter(items__product_id=product_id).distinct()
    
    status_dist = status_qs.values('status').annotate(count=Count('id')).order_by('status')
    status_data = {item['status']: item['count'] for item in status_dist}
    # Map to labels
    status_labels = ['Paid', 'Pending', 'Claim', 'Cancelled']
    status_counts = [
        status_data.get('paid', 0) + status_data.get('partial', 0), # Group partial with paid or separate? Let's group.
        status_data.get('pending', 0),
        status_data.get('claim', 0),
        status_data.get('cancelled', 0)
    ]

    # 8. Payment Methods (Doughnut)
    # Filter Payments by date range
    pay_qs = Payment.objects.filter(status='completed')
    if date_start: pay_qs = pay_qs.filter(payment_date__gte=date_start)
    if date_end: pay_qs = pay_qs.filter(payment_date__lte=date_end)
    if customer_id: pay_qs = pay_qs.filter(customer_id=customer_id)
    
    pay_methods = pay_qs.values('payment_method').annotate(total=Sum('amount')).order_by('-total')
    pay_method_labels = [p['payment_method'].replace('_', ' ').title() for p in pay_methods]
    pay_method_data = [float(p['total']) for p in pay_methods]

    # 9. Stem Length Popularity (Bar)
    stem_lengths = OrderItem.objects.filter(order__in=orders).values('stem_length_cm').annotate(
        qty=Sum('stems')
    ).order_by('stem_length_cm')
    stem_labels = [f"{s['stem_length_cm']}cm" for s in stem_lengths]
    stem_data = [s['qty'] for s in stem_lengths]

    # 10. Average Order Value (Line - Monthly)
    # Re-use monthly buckets logic but calculate Avg
    aov_data = []
    # monthly_labels already exists
    # reusing the loop range
    for i in range(12):
        month_date = timezone.now() - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Aggregates
        m_stats = orders.filter(date__range=[month_start, month_end]).aggregate(
            total=Sum('total_amount'), 
            count=Count('id')
        )
        total = m_stats['total'] or 0
        count = m_stats['count'] or 0
        avg = total / count if count > 0 else 0
        aov_data.append(float(avg))
    aov_data.reverse() # Match the reversed labels

    context = {
        'customers': Customer.objects.all(),
        'products': Product.objects.all(),
        # Basic
        'top_products': top_products_list,
        'customer_orders': customer_orders_list,
        'monthly_revenue': monthly_revenue,
        'monthly_labels': monthly_labels,
        'expense_categories': expense_categories_list,
        # Advanced
        'cp_mix': cp_mix_data,
        'daily_sales': {'labels': daily_labels, 'data': daily_sales},
        'status_dist': {'labels': status_labels, 'data': status_counts},
        'pay_methods': {'labels': pay_method_labels, 'data': pay_method_data},
        'stem_lengths': {'labels': stem_labels, 'data': stem_data},
        'aov_data': aov_data,
        
        # Pass filters back for UI state
        'filters': {
            'customer': int(customer_id) if customer_id else '',
            'product': int(product_id) if product_id else '',
            'date_start': date_start,
            'date_end': date_end,
        }
    }

    return render(request, 'graphs.html', context)
