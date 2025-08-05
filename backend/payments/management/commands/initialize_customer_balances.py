from django.core.management.base import BaseCommand
from customers.models import Customer
from payments.models import CustomerBalance


class Command(BaseCommand):
    help = 'Initialize customer balances for all existing customers'

    def handle(self, *args, **options):
        customers = Customer.objects.all()
        created_count = 0
        updated_count = 0

        for customer in customers:
            balance, created = CustomerBalance.objects.get_or_create(
                customer=customer,
                defaults={'currency': customer.preferred_currency}
            )

            # Recalculate balance
            old_balance = balance.current_balance
            new_balance = balance.recalculate_balance()

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created balance for {customer.name}: {new_balance} {balance.currency}')
                )
            elif old_balance != new_balance:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated balance for {customer.name}: {old_balance} → {new_balance} {balance.currency}')
                )
            else:
                self.stdout.write(
                    f'Balance for {customer.name}: {new_balance} {balance.currency} (unchanged)'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {customers.count()} customers. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
