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
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import json
import os

from .models import (
    Payment, PaymentType, PaymentAllocation, CustomerBalance,
    AccountStatement, PaymentLog
)
from customers.models import Customer
from orders.models import Order
from invoices.models import CreditNote
from .forms import CustomAccountStatementForm


@login_required
def payment_dashboard(request):
    """Main payment dashboard"""
    # Get summary statistics with proper rounding
    total_payments = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    total_payments = Decimal(str(total_payments)).quantize(Decimal('0.01'))

    total_outstanding = sum(
        customer.outstanding_amount() for customer in Customer.objects.all()
    ) or Decimal('0.00')
    total_outstanding = Decimal(str(total_outstanding)).quantize(Decimal('0.01'))

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

    # Calculate summary statistics with proper rounding
    total_payments = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    total_payments = Decimal(str(total_payments)).quantize(Decimal('0.01'))

    total_outstanding = sum(
        customer.outstanding_amount() for customer in Customer.objects.all()
    ) or Decimal('0.00')
    total_outstanding = Decimal(str(total_outstanding)).quantize(Decimal('0.01'))

    completed_count = Payment.objects.filter(status='completed').count()
    pending_count = Payment.objects.filter(status='pending').count()

    context = {
        'page_obj': page_obj,
        'customers': customers,
        'payment_types': payment_types,
        'filters': request.GET,
        'total_payments': total_payments,
        'total_outstanding': total_outstanding,
        'completed_count': completed_count,
        'pending_count': pending_count,
    }

    return render(request, 'payments/payment_list.html', context)


@login_required
def payment_detail(request, payment_id):
    """Detailed view of a payment"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    allocations = payment.allocations.all()

    # Get outstanding orders for this customer with payment status
    outstanding_orders = payment.customer.orders.filter(
        total_amount__gt=0
    ).order_by('date')

    # Add payment status and paid amount to each order
    for order in outstanding_orders:
        order.payment_status_display = order.get_payment_status_display()
        order.total_paid = order.total_paid_amount()
        order.outstanding = order.outstanding_amount()

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

            # Validate required fields
            if not all([customer_id, payment_type_id, amount, payment_method, payment_date]):
                messages.error(request, 'Please fill in all required fields.')
                raise ValueError('Missing required fields')

            # Validate amount
            try:
                amount = Decimal(amount)
                if amount <= 0:
                    messages.error(request, 'Payment amount must be greater than zero.')
                    raise ValueError('Invalid amount')
            except (ValueError, TypeError):
                messages.error(request, 'Please enter a valid amount.')
                raise ValueError('Invalid amount format')

            customer = Customer.objects.get(id=customer_id)
            payment_type = PaymentType.objects.get(id=payment_type_id)

            # Get status from form, default to 'completed'
            status = request.POST.get('status', 'completed')

            payment = Payment.objects.create(
                customer=customer,
                payment_type=payment_type,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                reference_number=reference_number,
                notes=notes,
                status=status,
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
            return redirect('payments:payment_detail', payment_id=payment.payment_id)

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
            return redirect('payments:payment_detail', payment_id=payment.payment_id)

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

    # Calculate statistics
    from datetime import datetime
    current_month = datetime.now()
    this_month_count = statements.filter(
        statement_date__year=current_month.year,
        statement_date__month=current_month.month
    ).count()
    pdf_ready_count = statements.filter(pdf_file__isnull=False).count()

    context = {
        'page_obj': page_obj,
        'customers': customers,
        'years': years,
        'filters': request.GET,
        'this_month_count': this_month_count,
        'pdf_ready_count': pdf_ready_count,
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
                customer=statement.customer,
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
            # Check if statement already exists for this month and update/regenerate it
            # The database has a unique constraint, so we must delete the old one first
            AccountStatement.objects.filter(
                customer=customer,
                statement_date=statement_date
            ).delete()

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
            return redirect('payments:account_statement_detail', statement_id=statement.id)

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
            amount = Decimal(str(item['amount']))

            # Validate that allocation doesn't exceed order outstanding amount
            if amount > order.outstanding_amount():
                return JsonResponse({
                    'success': False,
                    'error': f'Allocation amount {amount} exceeds outstanding amount {order.outstanding_amount()} for order {order.invoice_code}'
                }, status=400)

            allocation = PaymentAllocation.objects.create(
                payment=payment,
                order=order,
                amount=amount
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
@login_required
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


@login_required
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


@login_required
def generate_account_statement_pdf(request, statement_id):
    """Generate PDF for an account statement using ReportLab"""
    statement = get_object_or_404(AccountStatement, id=statement_id)

    try:
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
                    customer=statement.customer,
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

        # ReportLab PDF Generation
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.units import cm
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)

        elements = []
        styles = getSampleStyleSheet()

        # Custom Styles
        styles.add(ParagraphStyle(name='StatementTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#9A1D56'), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='SectionTitle', parent=styles['Heading3'], fontSize=12, spaceAfter=6, textColor=colors.HexColor('#9A1D56'), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=9))
        styles.add(ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white))
        
        # 1. Header Section
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        
        # Company Info
        company_info = [
            [Paragraph("<b>ZAHARA FLOWERS LIMITED</b>", styles['Normal'])],
            [Paragraph("P.O. Box 12345, Nairobi, Kenya", styles['NormalSmall'])],
            [Paragraph("Phone: +254 700 000 000", styles['NormalSmall'])],
            [Paragraph("Email: info@zaharaflowers.com", styles['NormalSmall'])],
            [Paragraph("Website: www.zaharaflowers.com", styles['NormalSmall'])]
        ]
        
        # Statement Info
        statement_info = [
            [Paragraph("<b>ACCOUNT STATEMENT</b>", styles['StatementTitle'])],
            [Paragraph(f"<b>Statement Date:</b> {statement.statement_date.strftime('%d %b, %Y')}", styles['Normal'])],
            [Paragraph(f"<b>Period:</b> {statement.start_date.strftime('%d %b, %Y')} - {statement.end_date.strftime('%d %b, %Y')}", styles['Normal'])],
            [Paragraph(f"<b>Statement #:</b> ST-{statement.id:06d}", styles['Normal'])]
        ]

        header_data = [[
            Image(logo_path, width=2.5*cm, height=2.5*cm) if os.path.exists(logo_path) else "",
            Table(company_info, style=[('VALIGN', (0,0), (-1,-1), 'TOP')]),
            Table(statement_info, style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (-1,-1), 'RIGHT')])
        ]]
        
        header_table = Table(header_data, colWidths=[3*cm, 8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#9A1D56')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.5*cm))

        # 2. Customer & Summary Section
        currency = statement.customer.preferred_currency
        
        customer_details = [
            [Paragraph("<b>Customer Details</b>", styles['SectionTitle'])],
            [Paragraph(f"<b>{statement.customer.name}</b>", styles['Normal'])],
        ]
        
        # Add email and phone only if they exist
        customer_email = getattr(statement.customer, 'email', None)
        if customer_email:
            customer_details.append([Paragraph(f"{customer_email}", styles['Normal'])])
            
        customer_phone = getattr(statement.customer, 'phone', None)
        if customer_phone:
            customer_details.append([Paragraph(f"{customer_phone}", styles['Normal'])])
            
        customer_details.append([Paragraph(f"Currency: {currency}", styles['Normal'])])
        
        summary_details = [
            [Paragraph("<b>Summary</b>", styles['SectionTitle'])],
            [Paragraph(f"Opening Balance: {currency} {statement.opening_balance}", styles['Normal'])],
            [Paragraph(f"Total Orders: {currency} {statement.total_orders}", styles['Normal'])],
            [Paragraph(f"Total Credits: {currency} {statement.total_credits}", styles['Normal'])],
            [Paragraph(f"Total Payments: {currency} {statement.total_payments}", styles['Normal'])],
            [Paragraph(f"<b>Closing Balance: {currency} {statement.closing_balance}</b>", styles['Normal'])]
        ]
        
        info_table = Table([[Table(customer_details), Table(summary_details)]], colWidths=[9.5*cm, 9.5*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))

        # 3. Transactions (Orders)
        if statement_data.get('orders'):
            elements.append(Paragraph("Orders & Invoices", styles['SectionTitle']))
            
            data = [[Paragraph('Date', styles['TableHeader']), Paragraph('Invoice #', styles['TableHeader']), 
                     Paragraph('Status', styles['TableHeader']), Paragraph('Amount', styles['TableHeader'])]]
            
            for order in statement_data['orders']:
                # Determine status color
                status_color = '#000000' # Default black
                if order.status == 'paid':
                    status_color = '#28a745' # Green
                elif order.status == 'pending':
                    status_color = '#fd7e14' # Orange
                elif order.status == 'cancelled':
                    status_color = '#6c757d' # Grey
                elif 'claim' in order.status:
                     status_color = '#dc3545' # Red

                data.append([
                    order.date.strftime('%d %b, %Y'),
                    order.invoice_code,
                    Paragraph(f"<font color='{status_color}'>{order.get_status_display()}</font>", styles['NormalSmall']),
                    f"{order.currency} {order.total_amount}"
                ])
                
            t = Table(data, colWidths=[4*cm, 5*cm, 5*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#9A1D56')), # Header bg
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('ALIGN', (-1,0), (-1,-1), 'RIGHT'), # Right align amounts
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.5*cm))

        # 4. Transactions (Credits)
        credits = statement_data.get('credits')
        if statement.include_credits and credits:
            elements.append(Paragraph("Credits & Adjustments", styles['SectionTitle']))
            
            data = [[Paragraph('Date', styles['TableHeader']), Paragraph('Credit Note #', styles['TableHeader']), 
                     Paragraph('Type', styles['TableHeader']), Paragraph('Amount', styles['TableHeader'])]]
            
            for credit in credits:
                data.append([
                    credit.created_at.strftime('%d %b, %Y'),
                    credit.code,
                    "Credit Note",
                    f"{credit.currency} {credit.total_amount}"
                ])
            
            t = Table(data, colWidths=[4*cm, 5*cm, 5*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#9A1D56')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.5*cm))

        # 5. Transactions (Payments)
        payments = statement_data.get('payments')
        if statement.include_payments and payments:
            elements.append(Paragraph("Payments Received", styles['SectionTitle']))
            
            data = [[Paragraph('Date', styles['TableHeader']), Paragraph('Payment #', styles['TableHeader']), 
                     Paragraph('Method', styles['TableHeader']), Paragraph('Amount', styles['TableHeader'])]]
            
            for payment in payments:
                data.append([
                    payment.payment_date.strftime('%d %b, %Y'),
                    Paragraph(str(payment.payment_id), styles['NormalSmall']),
                    payment.get_payment_method_display(),
                    f"{payment.currency} {payment.amount}"
                ])
                
            t = Table(data, colWidths=[3.5*cm, 6.5*cm, 4*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#9A1D56')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 1*cm))

        # 6. Reconciliation Summary
        elements.append(Paragraph("Balance Reconciliation", styles['SectionTitle']))
        
        recon_data = [
            ['Opening Balance', '+ New Orders', '- Credits', '- Payments', '= Closing Balance'],
            [f"{statement.opening_balance}", f"{statement.total_orders}", f"{statement.total_credits}", f"{statement.total_payments}", f"{statement.closing_balance}"]
        ]
        
        t = Table(recon_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 4*cm])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#9A1D56')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t)
        
        # 7. New Balance Highlight
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"<b>Amount Due: {currency} {statement.closing_balance}</b>", 
                                ParagraphStyle(name='AmountDue', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#9A1D56'))))

        # Build PDF
        doc.build(elements)
        pdf_value = buffer.getvalue()
        buffer.close()

        # Generate filename
        filename = f"Statement_{statement.customer.name}_{statement.statement_date.strftime('%Y_%m')}.pdf"
        filename = filename.replace(' ', '_').replace('/', '_')

        # Save to file system
        if not statement.pdf_file:
            pdf_path = os.path.join('account_statements_pdfs', filename)
            full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
            os.makedirs(os.path.dirname(full_pdf_path), exist_ok=True)
            with open(full_pdf_path, 'wb') as f:
                f.write(pdf_value)
            statement.pdf_file = pdf_path
            statement.save()

        # Return response
        response = HttpResponse(pdf_value, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('payments:account_statement_detail', statement_id=statement.id)


@login_required
def test_pdf_generation(request):
    """Test PDF generation to debug issues"""
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        # Create a simple test HTML
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test PDF</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #9A1D56; }
                .test-content { background: #f8f9fa; padding: 20px; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>Zahara Flowers - PDF Test</h1>
            <div class="test-content">
                <h2>PDF Generation Test</h2>
                <p>This is a test PDF to verify that WeasyPrint is working correctly.</p>
                <p>Generated at: {}</p>
                <p>If you can see this PDF, the PDF generation system is working!</p>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        print(f"Test HTML length: {len(test_html)}")

        # Generate PDF
        font_config = FontConfiguration()
        html_doc = HTML(string=test_html)
        pdf = html_doc.write_pdf(font_config=font_config)

        print(f"Generated PDF size: {len(pdf)} bytes")

        # Return PDF inline
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="test_pdf.pdf"'
        return response

    except ImportError as e:
        print(f"WeasyPrint import error: {str(e)}")
        messages.error(request, f'WeasyPrint not available: {str(e)}')
        return redirect('payments:account_statement_list')
    except Exception as e:
        print(f"WeasyPrint generation error: {str(e)}")
        messages.error(request, f'PDF test failed: {str(e)}')
        return redirect('payments:account_statement_list')


@login_required
def test_html_preview(request, statement_id):
    """Test HTML preview to debug template issues"""
    try:
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
                    customer=statement.customer,
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

        # Prepare context for PDF template
        context = {
            'statement': statement,
            'statement_data': statement_data,
            'logo_path': os.path.join(settings.STATIC_ROOT, 'images', 'logo.png') if hasattr(settings, 'STATIC_ROOT') else None,
        }

        # Render HTML template
        html_string = render_to_string('payments/account_statement_pdf.html', context)

        # Return HTML directly for debugging
        response = HttpResponse(html_string, content_type='text/html')
        return response

    except Exception as e:
        messages.error(request, f'Error generating HTML preview: {str(e)}')
        return redirect('payments:account_statement_detail', statement_id=statement.id)


@login_required
def recalculate_all_statements(request):
    """Recalculate all existing statements to fix missing payments"""
    if request.method == 'POST':
        try:
            statements = AccountStatement.objects.all()
            updated_count = 0

            for statement in statements:
                # Recalculate statement data
                statement.generate_statement_data()
                updated_count += 1

            messages.success(request, f'Successfully recalculated {updated_count} statements. All payments should now be included.')
            return redirect('payments:account_statement_list')

        except Exception as e:
            messages.error(request, f'Error recalculating statements: {str(e)}')
            return redirect('payments:account_statement_list')

    # GET request - show confirmation page
    context = {
        'statement_count': AccountStatement.objects.count(),
    }
    return render(request, 'payments/recalculate_statements.html', context)


def generate_custom_statement(request):
    """Generate custom account statements with different types and options"""
    if request.method == 'POST':
        form = CustomAccountStatementForm(request.POST)
        if form.is_valid():
            # Create the statement
            statement = form.save(commit=False)

            # Set statement date for custom statements
            if statement.statement_type in ['periodic', 'full_history']:
                from datetime import datetime
                # Use current date for custom statements
                statement.statement_date = datetime.now().date()
            else:
                statement.statement_date = form.cleaned_data['end_date']

            statement.generated_by = request.user.username if request.user.is_authenticated else 'System'

            # For full history, adjust dates to span from first order to today
            if statement.statement_type == 'full_history':
                from datetime import datetime
                first_order = Order.objects.filter(customer=statement.customer).order_by('date').first()
                if first_order:
                    statement.start_date = first_order.date
                    statement.end_date = datetime.now().date()  # Today's date

            # Prevent IntegrityError by removing existing conflicting statements
            AccountStatement.objects.filter(
                customer=statement.customer,
                statement_date=statement.statement_date
            ).delete()

            statement.save()

            # Generate statement data
            try:
                statement_data = statement.generate_statement_data()
                messages.success(request, f"Custom {statement.get_statement_type_display()} generated successfully!")
                return redirect('payments:account_statement_detail', statement_id=statement.id)
            except Exception as e:
                statement.delete()
                messages.error(request, f"Error generating statement: {str(e)}")
    else:
        form = CustomAccountStatementForm()

    context = {
        'form': form,
        'title': 'Generate Custom Account Statement',
        'subtitle': 'Create specialized statements for different business needs'
    }
    return render(request, 'payments/generate_custom_statement.html', context)
