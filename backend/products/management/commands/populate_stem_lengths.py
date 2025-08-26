from django.core.management.base import BaseCommand
from products.models import Product, CustomerProductPrice
from orders.models import OrderItem

class Command(BaseCommand):
    help = 'Populate stem_length_cm field for existing products and prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-length',
            type=int,
            default=50,
            help='Default stem length in centimeters for existing products'
        )

    def handle(self, *args, **options):
        default_length = options['default_length']

        # Update existing products
        products_updated = 0
        for product in Product.objects.filter(stem_length_cm__isnull=True):
            product.stem_length_cm = default_length
            product.save()
            products_updated += 1
            self.stdout.write(f"Updated product: {product.name} -> {default_length}cm")

        # Update existing customer product prices
        prices_updated = 0
        for price in CustomerProductPrice.objects.filter(stem_length_cm__isnull=True):
            price.stem_length_cm = default_length
            price.save()
            prices_updated += 1
            self.stdout.write(f"Updated price: {price.customer.name} - {price.product.name} -> {default_length}cm")

        # Update existing order items
        order_items_updated = 0
        for item in OrderItem.objects.filter(stem_length_cm__isnull=True):
            item.stem_length_cm = default_length
            item.save()
            order_items_updated += 1
            self.stdout.write(f"Updated order item: {item.product.name} in {item.order.invoice_code} -> {default_length}cm")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {products_updated} products, '
                f'{prices_updated} prices, and {order_items_updated} order items '
                f'with default stem length of {default_length}cm'
            )
        )









