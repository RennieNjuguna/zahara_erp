from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

# Model imports
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice
from orders.models import Order, OrderItem, CustomerOrderDefaults
from payments.models import Payment, PaymentType, PaymentAllocation, CustomerBalance, AccountStatement
from invoices.models import Invoice, CreditNote, CreditNoteItem
from expenses.models import Expense, ExpenseCategory, ExpenseAttachment
from employees.models import Employee
from planting_schedule.models import Crop, FarmBlock

# Serializer imports
from .serializers import (
    # Customer serializers
    CustomerSerializer, CustomerDetailSerializer, BranchSerializer,
    CustomerSummarySerializer, CustomerOrderDefaultsSerializer,

    # Product serializers
    ProductSerializer, CustomerProductPriceSerializer,

    # Order serializers
    OrderSerializer, OrderSummarySerializer, CreateOrderSerializer,
    OrderItemSerializer, CustomerOrderDefaultsSerializer,

    # Payment serializers
    PaymentSerializer, PaymentSummarySerializer, CreatePaymentSerializer,
    PaymentTypeSerializer, PaymentAllocationSerializer, PaymentAllocationRequestSerializer,
    CustomerBalanceSerializer, AccountStatementSerializer,

    # Invoice serializers
    InvoiceSerializer, CreditNoteSerializer, CreditNoteItemSerializer,
    CreateCreditNoteSerializer, CreateCreditNoteItemSerializer,

    # Expense serializers
    ExpenseSerializer, CreateExpenseSerializer, ExpenseCategorySerializer,
    ExpenseAttachmentSerializer,

    # Employee serializers
    EmployeeSerializer,

    # Planting schedule serializers
    CropSerializer, FarmBlockSerializer,

    # Analytics serializers
    DashboardStatsSerializer, SalesAnalyticsSerializer, PaymentAnalyticsSerializer,
)


# Customer Views
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'short_code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        customer = self.get_object()
        balance = customer.current_balance()
        return Response({
            'balance': str(balance),
            'currency': customer.preferred_currency
        })

    @action(detail=True, methods=['post'])
    def recalculate_balance(self, request, pk=None):
        customer = self.get_object()
        balance, created = CustomerBalance.objects.get_or_create(
            customer=customer,
            defaults={'currency': customer.preferred_currency}
        )
        new_balance = balance.recalculate_balance()
        return Response({
            'success': True,
            'balance': str(new_balance),
            'currency': customer.preferred_currency
        })

    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        customer = self.get_object()
        orders = customer.orders.all().order_by('-date')

        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)

        # Paginate
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderSummarySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderSummarySerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        customer = self.get_object()
        payments = Payment.objects.filter(customer=customer).order_by('-payment_date')

        # Paginate
        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = PaymentSummarySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PaymentSummarySerializer(payments, many=True)
        return Response(serializer.data)


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['customer']


# Product Views
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'stem_length_cm']
    ordering = ['name']


class CustomerProductPriceViewSet(viewsets.ModelViewSet):
    queryset = CustomerProductPrice.objects.all()
    serializer_class = CustomerProductPriceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['customer', 'product', 'stem_length_cm']


# Order Views
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['invoice_code']
    ordering_fields = ['date', 'total_amount', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateOrderSerializer
        return OrderSerializer

    @action(detail=True, methods=['post'])
    def mark_claim(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get('reason', 'Bad Produce')

        try:
            credit_note = order.mark_as_claim(reason)
            return Response({
                'success': True,
                'message': f'Order marked as claim. Credit note {credit_note.code} created.',
                'credit_note_id': credit_note.id
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get('reason', 'Order Cancelled')

        try:
            order.cancel_order(reason)
            return Response({
                'success': True,
                'message': f'Order {order.invoice_code} cancelled.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        order = self.get_object()
        items = order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class CustomerOrderDefaultsViewSet(viewsets.ModelViewSet):
    queryset = CustomerOrderDefaults.objects.all()
    serializer_class = CustomerOrderDefaultsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['customer', 'product']


# Payment Views
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['reference_number', 'notes', 'customer__name']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-payment_date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreatePaymentSerializer
        return PaymentSerializer

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        payment = self.get_object()
        allocations_data = request.data.get('allocations', [])

        try:
            total_allocation = sum(item['amount'] for item in allocations_data)
            if total_allocation > payment.unallocated_amount:
                return Response({
                    'success': False,
                    'error': 'Total allocation amount exceeds unallocated payment amount'
                }, status=status.HTTP_400_BAD_REQUEST)

            created_allocations = []
            for item in allocations_data:
                order = Order.objects.get(id=item['order_id'])
                amount = Decimal(str(item['amount']))

                if amount > order.outstanding_amount():
                    return Response({
                        'success': False,
                        'error': f'Allocation amount {amount} exceeds outstanding amount {order.outstanding_amount()} for order {order.invoice_code}'
                    }, status=status.HTTP_400_BAD_REQUEST)

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

            return Response({
                'success': True,
                'allocations': created_allocations,
                'remaining_amount': str(payment.unallocated_amount)
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def allocations(self, request, pk=None):
        payment = self.get_object()
        allocations = payment.allocations.all()
        serializer = PaymentAllocationSerializer(allocations, many=True)
        return Response(serializer.data)


class PaymentTypeViewSet(viewsets.ModelViewSet):
    queryset = PaymentType.objects.all()
    serializer_class = PaymentTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'mode']


class CustomerBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerBalance.objects.all()
    serializer_class = CustomerBalanceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['current_balance', 'last_updated']
    ordering = ['-current_balance']


class AccountStatementViewSet(viewsets.ModelViewSet):
    queryset = AccountStatement.objects.all()
    serializer_class = AccountStatementSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['statement_date', 'created_at']
    ordering = ['-statement_date']


# Invoice Views
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer


class CreditNoteViewSet(viewsets.ModelViewSet):
    queryset = CreditNote.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['code', 'title', 'reason']
    ordering_fields = ['created_at', 'total_credit_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateCreditNoteSerializer
        return CreditNoteSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        credit_note = self.get_object()

        try:
            credit_note.cancel_credit()
            return Response({
                'success': True,
                'message': f'Credit note {credit_note.code} cancelled.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        credit_note = self.get_object()
        items = credit_note.credit_note_items.all()
        serializer = CreditNoteItemSerializer(items, many=True)
        return Response(serializer.data)


class CreditNoteItemViewSet(viewsets.ModelViewSet):
    queryset = CreditNoteItem.objects.all()
    serializer_class = CreditNoteItemSerializer


# Expense Views
class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'reference_number', 'notes', 'vendor_name']
    ordering_fields = ['date_incurred', 'amount', 'created_at']
    ordering = ['-date_incurred']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateExpenseSerializer
        return ExpenseSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ExpenseAttachmentViewSet(viewsets.ModelViewSet):
    queryset = ExpenseAttachment.objects.all()
    serializer_class = ExpenseAttachmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['expense', 'file_type']


# Employee Views
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'position']
    ordering_fields = ['first_name', 'last_name', 'date_joined']
    ordering = ['first_name', 'last_name']


# Planting Schedule Views
class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'days_to_maturity']
    ordering = ['name']


class FarmBlockViewSet(viewsets.ModelViewSet):
    queryset = FarmBlock.objects.all()
    serializer_class = FarmBlockSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'area_acres']
    ordering = ['name']


# Analytics Views
class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Basic statistics
        total_orders = Order.objects.count()
        total_sales = Order.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        pending_orders = Order.objects.filter(status='pending').count()
        paid_orders = Order.objects.filter(status='paid').count()
        claim_orders = Order.objects.filter(status='claim').count()

        total_payments = Payment.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Calculate total outstanding
        total_outstanding = sum(
            customer.outstanding_amount() for customer in Customer.objects.all()
        ) or Decimal('0.00')

        # Top customers by sales
        top_customers = Customer.objects.annotate(
            total_sales=Sum('orders__total_amount')
        ).order_by('-total_sales')[:10]

        top_customers_data = []
        for customer in top_customers:
            top_customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'total_sales': str(customer.total_sales or Decimal('0.00'))
            })

        # Recent orders
        recent_orders = Order.objects.order_by('-date')[:10]
        recent_orders_data = OrderSummarySerializer(recent_orders, many=True).data

        # Recent payments
        recent_payments = Payment.objects.filter(status='completed').order_by('-payment_date')[:10]
        recent_payments_data = PaymentSummarySerializer(recent_payments, many=True).data

        # Monthly sales for the last 12 months
        monthly_sales = []
        for i in range(12):
            month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)

            month_orders = Order.objects.filter(
                date__gte=month_start,
                date__lt=month_end
            )

            month_sales = month_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            month_count = month_orders.count()

            monthly_sales.append({
                'month': month_start.strftime('%Y-%m'),
                'sales': str(month_sales),
                'orders': month_count
            })

        monthly_sales.reverse()  # Show oldest to newest

        stats_data = {
            'total_orders': total_orders,
            'total_sales': str(total_sales),
            'pending_orders': pending_orders,
            'paid_orders': paid_orders,
            'claim_orders': claim_orders,
            'total_payments': str(total_payments),
            'total_outstanding': str(total_outstanding),
            'top_customers': top_customers_data,
            'recent_orders': recent_orders_data,
            'recent_payments': recent_payments_data,
            'monthly_sales': monthly_sales
        }

        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)


class SalesAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', '30d')

        # Calculate date range
        if period == '7d':
            days = 7
        elif period == '30d':
            days = 30
        elif period == '90d':
            days = 90
        elif period == '1y':
            days = 365
        else:
            days = 30

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Sales data
        orders = Order.objects.filter(date__gte=start_date, date__lte=end_date)
        sales_data = orders.values('date').annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('date')

        # Customer data
        customers_data = orders.values('customer__name').annotate(
            total_sales=Sum('total_amount')
        ).order_by('-total_sales')[:10]

        analytics_data = {
            'period': period,
            'sales_data': list(sales_data),
            'orders_data': list(sales_data),  # Same data, different view
            'customers_data': list(customers_data)
        }

        serializer = SalesAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class PaymentAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', '30d')

        # Calculate date range
        if period == '7d':
            days = 7
        elif period == '30d':
            days = 30
        elif period == '90d':
            days = 90
        elif period == '1y':
            days = 365
        else:
            days = 30

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Payment methods breakdown
        payment_methods = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status='completed'
        ).values('payment_method').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        # Payment trends
        payment_trends = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status='completed'
        ).values('payment_date').annotate(
            total=Sum('amount')
        ).order_by('payment_date')

        # Top customers by payments
        top_customers = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status='completed'
        ).values('customer__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:10]

        analytics_data = {
            'period': period,
            'payment_methods': list(payment_methods),
            'payment_trends': list(payment_trends),
            'top_customers': list(top_customers)
        }

        serializer = PaymentAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


