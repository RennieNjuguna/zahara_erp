from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import Payment, PaymentAllocation, PaymentLog, CustomerBalance, AccountStatement
from orders.models import Order, OrderItem, CustomerOrderDefaults
from invoices.models import Invoice, CreditNote, CreditNoteItem
from customers.models import Customer, Branch
from products.models import Product, CustomerProductPrice
from expenses.models import Expense

class Command(BaseCommand):
    help = 'Wipes all transactional business data but preserves Users, Employees, and Configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run without manual confirmation',
        )

    def handle(self, *args, **options):
        if not options['force']:
            self.stdout.write(self.style.WARNING(
                'This will delete ALL business data (Orders, Payments, Customers, Products, etc.).\n'
                'Users and Employees will be PRESERVED.'
            ))
            confirm = input("Are you sure you want to continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        from django.db import connection

        # Disable foreign key checks for SQLite
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF;")

        with transaction.atomic():
            self.stdout.write("Deleting Payment & Financial Data...")
            PaymentAllocation.objects.all().delete()
            PaymentLog.objects.all().delete()
            CustomerBalance.objects.all().delete()
            AccountStatement.objects.all().delete()
            Payment.objects.all().delete()
            Expense.objects.all().delete()

            self.stdout.write("Deleting Credit Notes & Invoices...")
            CreditNoteItem.objects.all().delete()
            CreditNote.objects.all().delete()
            Invoice.objects.all().delete()

            self.stdout.write("Deleting Orders...")
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            CustomerOrderDefaults.objects.all().delete()

            self.stdout.write("Deleting Master Data (Price Lists, Branches, Customers)...")
            CustomerProductPrice.objects.all().delete()
            Branch.objects.all().delete()
            Customer.objects.all().delete()
            
            self.stdout.write("Deleting Products...")
            Product.objects.all().delete()

        # Re-enable foreign key checks
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON;")

        self.stdout.write(self.style.SUCCESS('Successfully wiped all business data.'))
