from django.core.management.base import BaseCommand
from orders.models import Order
from django.db.models import Sum
from decimal import Decimal


class Command(BaseCommand):
    help = 'Update order statuses based on payment allocations'

    def handle(self, *args, **options):
        self.stdout.write('Updating order statuses...')

        updated_count = 0
        for order in Order.objects.all():
            original_status = order.status

            # Check if order is paid
            if order.status == 'pending' and order.is_paid():
                order.status = 'paid'
                order.save(update_fields=['status'])
                updated_count += 1
                self.stdout.write(f'Updated {order.invoice_code} from {original_status} to {order.status}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} orders')
        )
