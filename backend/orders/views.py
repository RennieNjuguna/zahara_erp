from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from .models import CustomerOrderDefaults, Order, MissedSale
from customers.models import Customer, Branch
from products.models import Product
from django.contrib import messages
from django.db.models import Sum, Count
from decimal import Decimal


def order_list(request):
    customers = Customer.objects.all().order_by('name')
    customer_id = request.GET.get('customer')
    status = request.GET.get('status')
    date_filter = request.GET.get('date')

    orders = Order.objects.all().order_by('-date')
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    if status:
        orders = orders.filter(status=status)
    if date_filter:
        orders = orders.filter(date=date_filter)

    # Calculate summary statistics
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending')
    paid_orders = orders.filter(status='paid')
    claim_orders = orders.filter(status='claim')

    total_value = sum(order.total_amount for order in orders)
    pending_value = sum(order.total_amount for order in pending_orders)
    paid_value = sum(order.total_amount for order in paid_orders)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'customers': customers,
        'filters': request.GET,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
        'claim_orders': claim_orders,
        'total_value': total_value,
        'pending_value': pending_value,
        'paid_value': paid_value,
    })


def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    products = Product.objects.all().order_by('name')
    
    # Get associated credit notes
    from invoices.models import CreditNote, CreditNoteItem
    credit_notes = CreditNote.objects.filter(items__order_item__order=order).distinct()
    
    total_credits = CreditNoteItem.objects.filter(
        order_item__order=order,
        credit_note__status='approved'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'products': products,
        'credit_notes': credit_notes,
        'total_credits': total_credits,
    })


def order_create(request):
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')
    if request.method == 'POST':
        try:
            customer_id = int(request.POST.get('customer'))
            branch_id = request.POST.get('branch') or None
            date = request.POST.get('date')
            remarks = request.POST.get('remarks')
            logistics_provider = request.POST.get('logistics_provider')
            logistics_cost = request.POST.get('logistics_cost') or None

            logistics_provider = request.POST.get('logistics_provider')
            logistics_cost = request.POST.get('logistics_cost') or None

            order = Order.objects.create(
                customer_id=customer_id,
                branch_id=branch_id,
                date=date,
                remarks=remarks,
                logistics_provider=logistics_provider,
                logistics_cost=Decimal(logistics_cost) if logistics_cost else None,
                # AWB / Export Details
                invoice_template=request.POST.get('invoice_template', 'default'),
                awb_number=request.POST.get('awb_number'),
                flight_number=request.POST.get('flight_number'),
                agent_name=request.POST.get('agent_name'),
                mode_of_transport=request.POST.get('mode_of_transport'),
                inco_term=request.POST.get('inco_term'),
                deliver_to=request.POST.get('deliver_to'),
            )

            # Create initial items from arrays in the form
            product_ids = request.POST.getlist('item_product')
            stem_lengths = request.POST.getlist('item_stem_length_cm')
            boxes_list = request.POST.getlist('item_boxes')
            stems_per_box_list = request.POST.getlist('item_stems_per_box')
            price_list = request.POST.getlist('item_price_per_stem')

            if product_ids and any((pid or '').strip() for pid in product_ids):
                for idx, pid in enumerate(product_ids):
                    pid = (pid or '').strip()
                    if not pid:
                        continue
                    if not pid.isdigit():
                         continue
                    
                    # Clean input values
                    sl = stem_lengths[idx].strip() if idx < len(stem_lengths) else '0'
                    bx = boxes_list[idx].strip() if idx < len(boxes_list) else '0'
                    spb = stems_per_box_list[idx].strip() if idx < len(stems_per_box_list) else '0'
                    pps = price_list[idx].strip() if idx < len(price_list) else '0'

                    order.items.create(
                        product_id=int(pid),
                        stem_length_cm=int(sl) if sl else 0,
                        boxes=int(bx) if bx else 0,
                        stems_per_box=int(spb) if spb else 0,
                        price_per_stem=Decimal(pps) if pps else Decimal('0'),
                    )

            # Recalculate totals and trigger invoice regeneration via Order post_save signal
            order.save()

            messages.success(request, f'Order {order.invoice_code} created.')
            return redirect('orders:order_detail', order_id=order.id)
        except Exception as e:
            messages.error(request, f'Error creating order: {e}')

    return render(request, 'orders/order_form.html', {
        'customers': customers,
        'products': products,
        'default_currency': 'KES',  # Default currency
    })


def order_edit(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')

    if request.method == 'POST':
        try:
            order.customer_id = int(request.POST.get('customer'))
            order.branch_id = request.POST.get('branch') or None
            order.date = request.POST.get('date')
            order.remarks = request.POST.get('remarks')
            
            # AWB / Export Details
            order.invoice_template = request.POST.get('invoice_template', 'default')
            order.awb_number = request.POST.get('awb_number')
            order.flight_number = request.POST.get('flight_number')
            order.agent_name = request.POST.get('agent_name')
            order.mode_of_transport = request.POST.get('mode_of_transport')
            order.inco_term = request.POST.get('inco_term')
            order.deliver_to = request.POST.get('deliver_to')

            order.logistics_provider = request.POST.get('logistics_provider')
            logistics_cost = request.POST.get('logistics_cost') or None
            order.logistics_cost = Decimal(logistics_cost) if logistics_cost else None

            # Clear existing items and recreate from form data
            order.items.all().delete()

            # Create new items from arrays in the form
            product_ids = request.POST.getlist('item_product')
            stem_lengths = request.POST.getlist('item_stem_length_cm')
            boxes_list = request.POST.getlist('item_boxes')
            stems_per_box_list = request.POST.getlist('item_stems_per_box')
            price_list = request.POST.getlist('item_price_per_stem')

            if product_ids and any((pid or '').strip() for pid in product_ids):
                for idx, pid in enumerate(product_ids):
                    pid = (pid or '').strip()
                    if not pid:
                        continue
                    if not pid.isdigit():
                        continue

                    # Clean input values
                    sl = stem_lengths[idx].strip() if idx < len(stem_lengths) else '0'
                    bx = boxes_list[idx].strip() if idx < len(boxes_list) else '0'
                    spb = stems_per_box_list[idx].strip() if idx < len(stems_per_box_list) else '0'
                    pps = price_list[idx].strip() if idx < len(price_list) else '0'

                    order.items.create(
                        product_id=int(pid),
                        stem_length_cm=int(sl) if sl else 0,
                        boxes=int(bx) if bx else 0,
                        stems_per_box=int(spb) if spb else 0,
                        price_per_stem=Decimal(pps) if pps else Decimal('0'),
                    )

            order.save()
            messages.success(request, 'Order updated.')
            return redirect('orders:order_detail', order_id=order.id)
        except Exception as e:
            messages.error(request, f'Error updating order: {e}')

    return render(request, 'orders/order_form.html', {
        'order': order,
        'customers': customers,
        'products': products,
        'default_currency': order.currency or 'KES',  # Use order currency or default
    })


def order_item_add(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        try:
            product_id = int(request.POST.get('product'))
            stem_length_cm = int(request.POST.get('stem_length_cm'))
            boxes = int(request.POST.get('boxes'))
            stems_per_box = int(request.POST.get('stems_per_box'))
            price_per_stem = Decimal(request.POST.get('price_per_stem'))

            order.items.create(
                product_id=product_id,
                stem_length_cm=stem_length_cm,
                boxes=boxes,
                stems_per_box=stems_per_box,
                price_per_stem=price_per_stem,
            )
            # Recalculate totals and regenerate invoice
            order.save()
            messages.success(request, 'Item added.')
        except Exception as e:
            messages.error(request, f'Error adding item: {e}')
    return redirect('orders:order_detail', order_id=order.id)


def order_item_delete(request, item_id):
    from .models import OrderItem
    item = get_object_or_404(OrderItem, id=item_id)
    order_id = item.order_id
    item.delete()
    # Recalculate totals and regenerate invoice
    order = get_object_or_404(Order, id=order_id)
    order.save()
    messages.success(request, 'Item removed.')
    return redirect('orders:order_detail', order_id=order_id)


def get_branches(request):
    customer_id = request.GET.get('customer_id')
    if customer_id:
        branches = Branch.objects.filter(customer_id=customer_id)
        return JsonResponse([{'id': b.id, 'name': b.name} for b in branches], safe=False)
    return JsonResponse([], safe=False)


def get_orders(request):
    customer_id = request.GET.get('customer_id')
    if customer_id:
        orders = Order.objects.filter(customer_id=customer_id).order_by('-date')
        return JsonResponse([{
            'id': order.id,
            'invoice_code': order.invoice_code,
            'date': order.date.strftime('%Y-%m-%d'),
            'total_amount': str(order.total_amount)
        } for order in orders], safe=False)
    return JsonResponse([], safe=False)

@staff_member_required
@csrf_exempt
def get_defaults(request):
    """Get default stem length and price for a customer-product combination"""
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        product_id = request.POST.get('product_id')

        try:
            customer = Customer.objects.get(id=customer_id)
            product = Product.objects.get(id=product_id)

            defaults = CustomerOrderDefaults.get_defaults(customer, product)

            if defaults:
                return JsonResponse({
                    'success': True,
                    'stem_length_cm': defaults['stem_length_cm'],
                    'price_per_stem': str(defaults['price_per_stem'])
                })
            else:
                # Return product's default stem length if no customer defaults
                return JsonResponse({
                    'success': True,
                    'stem_length_cm': product.stem_length_cm,
                    'price_per_stem': None
                })

        except (Customer.DoesNotExist, Product.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Customer or product not found'
            })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })


def get_customer_pricing(request):
    """Get customer pricing for a specific product and stem length"""
    product_id = request.GET.get('product_id')
    stem_length = request.GET.get('stem_length')

    if not product_id or not stem_length:
        return JsonResponse({
            'success': False,
            'error': 'Product ID and stem length are required'
        })

    try:
        from products.models import CustomerProductPrice
        from customers.models import Customer

        # Validate inputs
        try:
            product_id = int(product_id)
            stem_length = int(stem_length)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid product ID or stem length format'
            })

        # Get all pricing data for this product and stem length
        pricing_data = CustomerProductPrice.objects.filter(
            product_id=product_id,
            stem_length_cm=stem_length
        ).select_related('customer', 'product').order_by('customer__name')

        pricing_list = []
        for price in pricing_data:
            pricing_list.append({
                'customer_name': price.customer.name,
                'product_name': price.product.name,
                'stem_length_cm': price.stem_length_cm,
                'price_per_stem': str(price.price_per_stem),
                'currency': price.customer.preferred_currency
            })

        return JsonResponse({
            'success': True,
            'pricing': pricing_list,
            'count': len(pricing_list)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def missed_sales_list(request):
    """List missed sales, show summary metrics, and analytics with KES conversion"""
    from payments.models import ExchangeRate
    from collections import defaultdict
    from datetime import datetime
    import json
    
    # Determine target currency
    target_currency = 'KES'
    if request.user.is_authenticated:
        try:
            from core.models import UserPreference
            target_currency = request.user.preferences.currency
        except (ImportError, AttributeError, UserPreference.DoesNotExist):
            pass

    missed_sales = MissedSale.objects.select_related('customer', 'product').order_by('-date')
    
    # --- Currency Conversion Helper ---
    # Cache rates to avoid N queries
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
        if rate_from_ksh == 0: return amount_in_ksh
        return amount_in_ksh / rate_from_ksh

    # --- Calculations ---
    total_missed_qty = 0
    potential_revenue = Decimal('0.00')
    
    # Analytics Buckets
    monthly_data = defaultdict(lambda: {'qty': 0, 'val': Decimal('0.00')})
    product_data = defaultdict(lambda: {'qty': 0, 'val': Decimal('0.00')})

    # Iterate in Python to handle multi-currency conversion
    # Note: If missed_sales gets very large, this should be optimized or paginated,
    # but for typical "missed sales" volumes (hundreds/thousands), this is fine.
    for sale in missed_sales:
        total_missed_qty += sale.quantity
        
        # Calculate Value
        price = sale.price_per_stem
        if price:
            currency = sale.customer.preferred_currency
            
            # Local value
            local_val = price * sale.quantity
            # Converted value
            base_val = convert_currency(local_val, currency, target_currency)
            
            potential_revenue += base_val
            
            # Add to Monthly Trend
            month_key = sale.date.strftime('%Y-%m') # YYYY-MM for sorting
            monthly_data[month_key]['qty'] += sale.quantity
            monthly_data[month_key]['val'] += base_val
            
            # Add to Product Breakdown
            prod_name = sale.product.name
            product_data[prod_name]['qty'] += sale.quantity
            product_data[prod_name]['val'] += base_val

    # --- Prepare Chart Data ---
    # 1. Monthly Trend
    sorted_months = sorted(monthly_data.keys())
    chart_months = []
    chart_qtys = []
    chart_vals = []
    
    for month in sorted_months:
        # Format month label like "Jan 2025"
        dt = datetime.strptime(month, '%Y-%m')
        chart_months.append(dt.strftime('%b %Y'))
        chart_qtys.append(monthly_data[month]['qty'])
        chart_vals.append(float(monthly_data[month]['val']))

    # 2. Product Breakdown (Top 5 by Value)
    sorted_products = sorted(product_data.items(), key=lambda x: x[1]['val'], reverse=True)[:5]
    prod_labels = []
    prod_vals = []
    
    for prod_name, data in sorted_products:
        prod_labels.append(prod_name)
        prod_vals.append(float(data['val']))

    context = {
        'missed_sales': missed_sales,
        'total_missed_qty': total_missed_qty,
        'potential_revenue': potential_revenue,
        'currency_label': target_currency,
        'top_missing': MissedSale.objects.values('product__name').annotate(total_qty=Sum('quantity'), requests=Count('id')).order_by('-total_qty')[:5],
        
        # Chart Data
        'chart_months': json.dumps(chart_months),
        'chart_qtys': json.dumps(chart_qtys),
        'chart_vals': json.dumps(chart_vals),
        'chart_prod_labels': json.dumps(prod_labels),
        'chart_prod_vals': json.dumps(prod_vals),
    }
    return render(request, 'orders/missed_sales_list.html', context)


def missed_sale_create(request):
    """Record a new missed sale"""
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer')
            product_id = request.POST.get('product')
            quantity = request.POST.get('quantity')
            reason = request.POST.get('reason')
            notes = request.POST.get('notes')
            date = request.POST.get('date')
            
            # New fields
            stem_length_cm = request.POST.get('stem_length_cm') or 0
            price_per_stem = request.POST.get('price_per_stem') or None

            MissedSale.objects.create(
                customer_id=customer_id,
                product_id=product_id,
                quantity=quantity,
                reason=reason,
                notes=notes,
                date=date,
                stem_length_cm=int(stem_length_cm),
                price_per_stem=Decimal(price_per_stem) if price_per_stem else None
            )
            messages.success(request, 'Missed sale recorded successfully.')
            return redirect('orders:missed_sales_list')
        except Exception as e:
            messages.error(request, f'Error recording missed sale: {str(e)}')
            
    context = {
        'customers': customers,
        'products': products,
        'reason_choices': MissedSale.REASON_CHOICES,
        'title': 'Record Missed Sale',
        'submit_text': 'Record Missed Sale'
    }
    return render(request, 'orders/missed_sale_form.html', context)


def missed_sale_edit(request, pk):
    """Edit an existing missed sale"""
    missed_sale = get_object_or_404(MissedSale, pk=pk)
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')
    
    if request.method == 'POST':
        try:
            missed_sale.customer_id = request.POST.get('customer')
            missed_sale.product_id = request.POST.get('product')
            missed_sale.quantity = request.POST.get('quantity')
            missed_sale.reason = request.POST.get('reason')
            missed_sale.notes = request.POST.get('notes')
            missed_sale.date = request.POST.get('date')
            
            stem_length = request.POST.get('stem_length_cm')
            missed_sale.stem_length_cm = int(stem_length) if stem_length else 0
            
            price_val = request.POST.get('price_per_stem')
            missed_sale.price_per_stem = Decimal(price_val) if price_val else None

            missed_sale.save()
            messages.success(request, 'Missed sale updated successfully.')
            return redirect('orders:missed_sales_list')
        except Exception as e:
            messages.error(request, f'Error updating missed sale: {str(e)}')

    context = {
        'missed_sale': missed_sale,
        'customers': customers,
        'products': products,
        'reason_choices': MissedSale.REASON_CHOICES,
        'title': 'Edit Missed Sale',
        'submit_text': 'Update Missed Sale'
    }
    return render(request, 'orders/missed_sale_form.html', context)


def missed_sale_delete(request, pk):
    """Delete a missed sale"""
    if request.method == 'POST':
        missed_sale = get_object_or_404(MissedSale, pk=pk)
        missed_sale.delete()
        messages.success(request, 'Missed sale deleted successfully.')
    return redirect('orders:missed_sales_list')


def email_invoice(request, order_id):
    """View to compose and send invoice via email"""
    from core.utils.email import send_invoice_email, fetch_recent_threads, get_email_config
    
    order = get_object_or_404(Order, id=order_id)
    config = get_email_config(request.user)
    has_config = bool(config)
    
    # Check if PDF exists, if not try to regenerate
    # Access via related invoice object
    invoice = getattr(order, 'invoice', None)
    
    if not invoice or not invoice.pdf_file:
         from invoices.utils import generate_invoice_pdf
         from invoices.models import Invoice
         # Get related invoice (should be only one usually, catch issues)
         try:
             if not invoice:
                 invoice, _ = Invoice.objects.get_or_create(order=order, defaults={'invoice_code': order.invoice_code})
             
             generate_invoice_pdf(invoice)
             invoice.refresh_from_db()
         except Exception as e:
             messages.warning(request, f"Could not generate invoice PDF: {e}")

    if request.method == 'POST' and has_config:
        recipient = request.POST.get('recipient')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        thread_id = request.POST.get('thread_id')
        
        try:
            # Send Email
            if invoice and invoice.pdf_file:
                attachment_path = invoice.pdf_file.path
            else:
                attachment_path = None
                
            send_invoice_email(
                request.user, 
                recipient, 
                subject, 
                body, 
                attachment_path=attachment_path,
                in_reply_to_id=thread_id
            )
            messages.success(request, f'Invoice sent successfully to {recipient}!')
            return redirect('orders:order_detail', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')
    
    # Fetch recent threads if configured
    recent_threads = []
    if has_config and order.customer.email:
         recent_threads = fetch_recent_threads(request.user, order.customer.email, limit=5)

    return render(request, 'orders/email_invoice.html', {
        'order': order,
        'has_config': has_config,
        'threads': recent_threads
    })
