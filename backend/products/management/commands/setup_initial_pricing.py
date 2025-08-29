from django.core.management.base import BaseCommand
from products.models import Product, CustomerProductPrice
from customers.models import Customer
from decimal import Decimal

class Command(BaseCommand):
    help = 'Set up initial customer pricing for products with different stem lengths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-id',
            type=int,
            help='Customer ID to set pricing for (optional)'
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Product ID to set pricing for (optional)'
        )
        parser.add_argument(
            '--stem-length',
            type=int,
            default=50,
            help='Stem length in centimeters (default: 50)'
        )
        parser.add_argument(
            '--price',
            type=float,
            default=0.50,
            help='Price per stem (default: 0.50)'
        )

    def handle(self, *args, **options):
        customer_id = options.get('customer_id')
        product_id = options.get('product_id')
        stem_length = options.get('stem_length')
        price = Decimal(str(options.get('price')))

        # Get customers and products to work with
        if customer_id:
            customers = Customer.objects.filter(id=customer_id)
        else:
            customers = Customer.objects.all()

        if product_id:
            products = Product.objects.filter(id=product_id)
        else:
            products = Product.objects.all()

        if not customers.exists():
            self.stdout.write(self.style.ERROR('No customers found'))
            return

        if not products.exists():
            self.stdout.write(self.style.ERROR('No products found'))
            return

        # Set up pricing
        created_count = 0
        updated_count = 0

        for customer in customers:
            for product in products:
                # Check if pricing already exists
                pricing, created = CustomerProductPrice.objects.get_or_create(
                    customer=customer,
                    product=product,
                    stem_length_cm=stem_length,
                    defaults={'price_per_stem': price}
                )

                if created:
                    self.stdout.write(
                        f"Created pricing: {customer.name} - {product.name} @ {stem_length}cm: ${price}"
                    )
                    created_count += 1
                else:
                    # Update existing pricing
                    if pricing.price_per_stem != price:
                        pricing.price_per_stem = price
                        pricing.save()
                        self.stdout.write(
                            f"Updated pricing: {customer.name} - {product.name} @ {stem_length}cm: ${price}"
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            f"Pricing already exists: {customer.name} - {product.name} @ {stem_length}cm: ${price}"
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count} new pricing records and {updated_count} updates'
            )
        )










