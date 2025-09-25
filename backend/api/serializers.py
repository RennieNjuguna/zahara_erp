from rest_framework import serializers
from django.contrib.auth.models import User
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice
from orders.models import Order, OrderItem, CustomerOrderDefaults
from payments.models import Payment, PaymentType, PaymentAllocation, CustomerBalance, AccountStatement, PaymentLog
from invoices.models import Invoice, CreditNote, CreditNoteItem
from expenses.models import Expense, ExpenseCategory, ExpenseAttachment
from employees.models import Employee
from planting_schedule.models import Crop, FarmBlock


# Authentication Serializers
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']
        read_only_fields = ['id', 'username']


# Customer Serializers
class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'short_code', 'customer']
        read_only_fields = ['id']


class CustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'short_code', 'preferred_currency']


class CustomerSerializer(serializers.ModelSerializer):
    branches = BranchSerializer(many=True, read_only=True)
    order_statistics = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()
    
    def get_order_statistics(self, obj):
        return obj.get_order_statistics()
    
    def get_current_balance(self, obj):
        return obj.current_balance()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'short_code', 'preferred_currency',
            'branches', 'order_statistics', 'current_balance'
        ]


class CustomerDetailSerializer(CustomerSerializer):
    recent_orders = serializers.SerializerMethodField()
    payment_history = serializers.SerializerMethodField()
    
    def get_recent_orders(self, obj):
        orders = obj.orders.all().order_by('-date')[:10]
        return OrderSummarySerializer(orders, many=True).data
    
    def get_payment_history(self, obj):
        payments = Payment.objects.filter(customer=obj).order_by('-payment_date')[:10]
        return PaymentSummarySerializer(payments, many=True).data
    
    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + [
            'recent_orders', 'payment_history'
        ]


# Product Serializers
class ProductSerializer(serializers.ModelSerializer):
    customer_prices = serializers.SerializerMethodField()
    
    def get_customer_prices(self, obj):
        prices = obj.customer_prices.all()[:10]  # Limit for performance
        return CustomerProductPriceSerializer(prices, many=True).data
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'stem_length_cm', 'customer_prices']


class CustomerProductPriceSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = CustomerProductPrice
        fields = [
            'id', 'customer', 'product', 'stem_length_cm', 
            'price_per_stem', 'last_updated'
        ]
        read_only_fields = ['id']


# Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'stem_length_cm', 'boxes', 
            'stems_per_box', 'stems', 'price_per_stem', 'total_amount'
        ]


class OrderSummarySerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'invoice_code', 'customer', 'total_amount', 
            'currency', 'date', 'status'
        ]


class CreditNoteSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = ['id', 'code', 'total_credit_amount', 'status', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = CustomerSummarySerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    payment_status = serializers.SerializerMethodField()
    outstanding_amount = serializers.SerializerMethodField()
    total_paid_amount = serializers.SerializerMethodField()
    credit_notes = serializers.SerializerMethodField()
    
    def get_payment_status(self, obj):
        return obj.payment_status()
    
    def get_outstanding_amount(self, obj):
        return str(obj.outstanding_amount())
    
    def get_total_paid_amount(self, obj):
        return str(obj.total_paid_amount())
    
    def get_credit_notes(self, obj):
        credit_notes = obj.credit_notes.all()
        return CreditNoteSummarySerializer(credit_notes, many=True).data
    
    class Meta:
        model = Order
        fields = [
            'id', 'invoice_code', 'customer', 'branch', 'total_amount',
            'currency', 'date', 'status', 'status_reason', 'remarks',
            'logistics_provider', 'logistics_cost', 'tracking_number',
            'delivery_status', 'items', 'payment_status', 'outstanding_amount',
            'total_paid_amount', 'credit_notes'
        ]


class CreateOrderItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    stem_length_cm = serializers.IntegerField()
    boxes = serializers.IntegerField()
    stems_per_box = serializers.IntegerField()
    price_per_stem = serializers.DecimalField(max_digits=10, decimal_places=2)


class CreateOrderSerializer(serializers.ModelSerializer):
    items = CreateOrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'customer', 'branch', 'date', 'remarks', 'logistics_provider',
            'logistics_cost', 'tracking_number', 'delivery_status', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        return order


class CustomerOrderDefaultsSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = CustomerOrderDefaults
        fields = [
            'id', 'customer', 'product', 'stem_length_cm', 
            'price_per_stem', 'last_used'
        ]


# Payment Serializers
class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentType
        fields = ['id', 'name', 'mode', 'description', 'is_active']


class PaymentAllocationSerializer(serializers.ModelSerializer):
    order = OrderSummarySerializer(read_only=True)
    
    class Meta:
        model = PaymentAllocation
        fields = ['id', 'order', 'amount', 'allocated_at']


class PaymentSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    payment_type = PaymentTypeSerializer(read_only=True)
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    allocated_amount = serializers.ReadOnlyField()
    unallocated_amount = serializers.ReadOnlyField()
    is_fully_allocated = serializers.ReadOnlyField()
    
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'customer', 'payment_type', 'amount', 'currency',
            'payment_method', 'payment_date', 'status', 'reference_number',
            'notes', 'allocations', 'allocated_amount', 'unallocated_amount',
            'is_fully_allocated', 'created_at', 'updated_at'
        ]


class CreatePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'customer', 'payment_type', 'amount', 'payment_method',
            'payment_date', 'reference_number', 'notes', 'status'
        ]


class PaymentAllocationRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class PaymentSummarySerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'customer', 'amount', 'currency', 
            'payment_date', 'status', 'reference_number'
        ]


class CustomerBalanceSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    
    class Meta:
        model = CustomerBalance
        fields = [
            'id', 'customer', 'current_balance', 'currency', 'last_updated'
        ]


class AccountStatementSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    
    class Meta:
        model = AccountStatement
        fields = [
            'id', 'customer', 'statement_type', 'statement_date', 
            'start_date', 'end_date', 'opening_balance', 'closing_balance',
            'total_orders', 'total_credits', 'total_payments',
            'pdf_file', 'created_at', 'generated_by'
        ]


# Invoice Serializers
class InvoiceSerializer(serializers.ModelSerializer):
    order = OrderSummarySerializer(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'invoice_code', 'pdf_file', 
            'created_at', 'last_updated'
        ]


class CreditNoteItemSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(read_only=True)
    
    class Meta:
        model = CreditNoteItem
        fields = [
            'id', 'order_item', 'stems_affected', 'credit_amount', 'reason'
        ]


class CreditNoteSerializer(serializers.ModelSerializer):
    order = OrderSummarySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    items = CreditNoteItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = CreditNote
        fields = [
            'id', 'code', 'order', 'title', 'reason', 'total_credit_amount',
            'currency', 'status', 'credit_type', 'created_by', 'created_at',
            'updated_at', 'applied_at', 'items'
        ]


class CreateCreditNoteItemSerializer(serializers.Serializer):
    order_item = serializers.IntegerField()
    stems_affected = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)


class CreateCreditNoteSerializer(serializers.ModelSerializer):
    items = CreateCreditNoteItemSerializer(many=True)
    
    class Meta:
        model = CreditNote
        fields = ['order', 'title', 'reason', 'items']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        credit_note = CreditNote.objects.create(**validated_data)
        
        for item_data in items_data:
            CreditNoteItem.objects.create(credit_note=credit_note, **item_data)
        
        return credit_note


# Expense Serializers
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = [
            'id', 'name', 'description', 'color', 'is_active',
            'created_at', 'updated_at'
        ]


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseAttachment
        fields = [
            'id', 'file', 'file_type', 'original_filename', 
            'description', 'uploaded_at'
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    category = ExpenseCategorySerializer(read_only=True)
    attachments = ExpenseAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'name', 'amount', 'currency', 'reference_number',
            'category', 'description', 'date_incurred', 'due_date',
            'status', 'approved_by', 'approved_at', 'rejection_reason',
            'payment_method', 'payment_date', 'vendor_name', 'vendor_contact',
            'is_recurring', 'recurring_frequency', 'tags', 'created_by',
            'created_at', 'updated_at', 'attachments'
        ]


class CreateExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'name', 'amount', 'currency', 'reference_number', 'category',
            'description', 'date_incurred', 'due_date', 'payment_method',
            'payment_date', 'vendor_name', 'vendor_contact', 'is_recurring',
            'recurring_frequency', 'tags'
        ]


# Employee Serializers
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 'first_name', 'last_name', 'position', 
            'email', 'phone_number', 'date_joined'
        ]


# Planting Schedule Serializers
class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ['id', 'name', 'description', 'days_to_maturity', 'created_at']


class FarmBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmBlock
        fields = [
            'id', 'name', 'description', 'area_acres', 'status', 'created_at'
        ]


# Analytics Serializers
class DashboardStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_orders = serializers.IntegerField()
    paid_orders = serializers.IntegerField()
    claim_orders = serializers.IntegerField()
    total_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    top_customers = serializers.ListField()
    recent_orders = serializers.ListField()
    recent_payments = serializers.ListField()
    monthly_sales = serializers.ListField()


class SalesAnalyticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    sales_data = serializers.ListField()
    orders_data = serializers.ListField()
    customers_data = serializers.ListField()


class PaymentAnalyticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    payment_methods = serializers.ListField()
    payment_trends = serializers.ListField()
    top_customers = serializers.ListField()


