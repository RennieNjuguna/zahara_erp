from django.core.management.base import BaseCommand
from orders.models import Order


class Command(BaseCommand):
    help = 'Set default status for orders that do not have the new status choices'

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

        # Find orders with old status values (not in new choices)
        old_statuses = ['original', 'edited']  # Old status values
        orders_to_update = Order.objects.filter(status__in=old_statuses)

        total_orders = orders_to_update.count()

        if total_orders == 0:
            self.stdout.write(self.style.SUCCESS('No orders found with old status values.'))
            return

        self.stdout.write(f'Found {total_orders} orders with old status values:')

        for order in orders_to_update:
            self.stdout.write(f'  {order.invoice_code}: {order.status} → pending')

        if not dry_run:
            # Update all orders to pending
            updated_count = orders_to_update.update(status='pending')
            self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated_count} orders to pending status.'))
        else:
            self.stdout.write(self.style.WARNING(f'\nWould update {total_orders} orders to pending status.'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes.'))
