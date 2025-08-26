from django.core.management.base import BaseCommand
from customers.models import Customer
from products.models import Product, CustomerProductPrice
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create sample customer pricing data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample customer pricing data...')

        # Get or create some sample data
        customers = Customer.objects.all()[:3]  # Get first 3 customers
        products = Product.objects.all()[:3]    # Get first 3 products

        if not customers.exists():
            self.stdout.write(self.style.ERROR('No customers found. Please create customers first.'))
            return

        if not products.exists():
            self.stdout.write(self.style.ERROR('No products found. Please create products first.'))
            return

        # Create sample pricing data
        stem_lengths = [40, 50, 60, 70, 80]
        created_count = 0

        for customer in customers:
            for product in products:
                for stem_length in stem_lengths:
                    # Create different prices for different combinations
                    base_price = Decimal('2.50') + (stem_length - 40) * Decimal('0.10')

                    # Add some variation based on customer
                    if customer.name.startswith('A'):
                        price = base_price * Decimal('1.1')  # 10% higher
                    elif customer.name.startswith('B'):
                        price = base_price * Decimal('0.9')  # 10% lower
                    else:
                        price = base_price

                    # Round to 2 decimal places
                    price = round(price, 2)

                    # Create or update the pricing
                    pricing, created = CustomerProductPrice.objects.get_or_create(
                        customer=customer,
                        product=product,
                        stem_length_cm=stem_length,
                        defaults={'price_per_stem': price}
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            f'Created: {customer.name} - {product.name} @ {stem_length}cm: {price} {customer.preferred_currency}'
                        )
                    else:
                        # Update existing price
                        pricing.price_per_stem = price
                        pricing.save()
                        self.stdout.write(
                            f'Updated: {customer.name} - {product.name} @ {stem_length}cm: {price} {customer.preferred_currency}'
                        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {created_count} pricing records!')
        )

