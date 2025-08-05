from django.core.management.base import BaseCommand
from payments.models import PaymentType


class Command(BaseCommand):
    help = 'Set up initial payment types for the system'

    def handle(self, *args, **options):
        payment_types = [
            {
                'name': 'Per Order Payment',
                'mode': 'per_order',
                'description': 'Payment made for a specific order'
            },
            {
                'name': 'Bulk Payment',
                'mode': 'bulk',
                'description': 'Payment made for multiple orders or to reduce outstanding balance'
            },
            {
                'name': 'Monthly Payment',
                'mode': 'monthly',
                'description': 'Regular monthly payment to settle outstanding balances'
            },
        ]

        created_count = 0
        for pt_data in payment_types:
            payment_type, created = PaymentType.objects.get_or_create(
                name=pt_data['name'],
                defaults={
                    'mode': pt_data['mode'],
                    'description': pt_data['description'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created payment type: {payment_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Payment type already exists: {payment_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully set up {created_count} payment types')
        )
