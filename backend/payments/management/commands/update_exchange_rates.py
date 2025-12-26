from django.core.management.base import BaseCommand
from payments.utils import fetch_and_update_rates

class Command(BaseCommand):
    help = 'Fetches live exchange rates and updates the database'

    def handle(self, *args, **options):
        self.stdout.write('Fetching exchange rates...')
        success, message = fetch_and_update_rates()
        
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(f'Error: {message}'))
