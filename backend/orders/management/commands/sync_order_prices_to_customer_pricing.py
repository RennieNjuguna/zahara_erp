from django.core.management.base import BaseCommand
from orders.models import Order

class Command(BaseCommand):
    help = 'Sync all existing order prices to CustomerProductPrice'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='Specific order ID to sync (optional)'
        )
        parser.add_argument(
            '--customer-id',
            type=int,
            help='Customer ID to sync orders for (optional)'
        )

    def handle(self, *args, **options):
        order_id = options.get('order_id')
        customer_id = options.get('customer_id')

        # Get orders to sync
        if order_id:
            orders = Order.objects.filter(id=order_id)
        elif customer_id:
            orders = Order.objects.filter(customer_id=customer_id)
        else:
            orders = Order.objects.all()

        if not orders.exists():
            self.stdout.write(self.style.ERROR('No orders found'))
            return

        # Sync prices
        total_synced = 0
        for order in orders:
            synced_count = order.sync_prices_to_customer_pricing()
            total_synced += synced_count
            if synced_count > 0:
                self.stdout.write(f"Synced {synced_count} prices from order {order.invoice_code}")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully synced {total_synced} prices to CustomerProductPrice'
            )
        )










