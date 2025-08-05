from django.core.management.base import BaseCommand
from orders.models import Order
from payments.models import PaymentAllocation
from invoices.models import CreditNote
from django.db.models import Sum
from decimal import Decimal


class Command(BaseCommand):
    help = 'Update all existing orders to have correct status based on payment allocations and claims'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write('DRY RUN MODE - No changes will be made')
            self.stdout.write('=' * 50)

        # Get all orders
        orders = Order.objects.all()
        total_orders = orders.count()

        self.stdout.write(f'Processing {total_orders} orders...')

        # Statistics
        stats = {
            'updated_to_pending': 0,
            'updated_to_paid': 0,
            'updated_to_claim': 0,
            'already_correct': 0,
            'errors': 0
        }

        for order in orders:
            try:
                original_status = order.status
                new_status = self.determine_order_status(order)

                if original_status != new_status:
                    if not dry_run:
                        order.status = new_status
                        order.save(update_fields=['status'])

                    stats[f'updated_to_{new_status}'] += 1
                    self.stdout.write(
                        f'Order {order.invoice_code}: {original_status} → {new_status}'
                    )
                else:
                    stats['already_correct'] += 1

            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing order {order.invoice_code}: {str(e)}')
                )

        # Print summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('SUMMARY:')
        self.stdout.write(f'Total orders processed: {total_orders}')
        self.stdout.write(f'Updated to pending: {stats["updated_to_pending"]}')
        self.stdout.write(f'Updated to paid: {stats["updated_to_paid"]}')
        self.stdout.write(f'Updated to claim: {stats["updated_to_claim"]}')
        self.stdout.write(f'Already correct: {stats["already_correct"]}')
        self.stdout.write(f'Errors: {stats["errors"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. No changes were made.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nOrder statuses updated successfully!'))

    def determine_order_status(self, order):
        """Determine the correct status for an order based on payments and claims"""

        # Check if order has claims (credit notes)
        has_claims = CreditNote.objects.filter(order=order).exists()
        if has_claims:
            return 'claim'

        # Check if order is fully paid
        if order.is_paid():
            return 'paid'

        # Default to pending
        return 'pending'
