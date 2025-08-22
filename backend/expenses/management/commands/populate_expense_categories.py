from django.core.management.base import BaseCommand
from expenses.models import ExpenseCategory


class Command(BaseCommand):
    help = 'Populate initial expense categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Office Supplies',
                'description': 'Office equipment, stationery, and supplies',
                'color': '#007bff'
            },
            {
                'name': 'Travel & Transportation',
                'description': 'Fuel, vehicle maintenance, public transport, flights',
                'color': '#28a745'
            },
            {
                'name': 'Marketing & Advertising',
                'description': 'Promotional materials, online ads, events',
                'color': '#ffc107'
            },
            {
                'name': 'Utilities',
                'description': 'Electricity, water, internet, phone bills',
                'color': '#17a2b8'
            },
            {
                'name': 'Rent & Maintenance',
                'description': 'Office rent, building maintenance, repairs',
                'color': '#6c757d'
            },
            {
                'name': 'Professional Services',
                'description': 'Legal fees, accounting, consulting',
                'color': '#dc3545'
            },
            {
                'name': 'Equipment & Technology',
                'description': 'Computers, software, machinery',
                'color': '#6f42c1'
            },
            {
                'name': 'Employee Benefits',
                'description': 'Health insurance, training, team events',
                'color': '#fd7e14'
            },
            {
                'name': 'Inventory & Supplies',
                'description': 'Raw materials, packaging, production supplies',
                'color': '#20c997'
            },
            {
                'name': 'Other',
                'description': 'Miscellaneous expenses not covered above',
                'color': '#6c757d'
            }
        ]

        created_count = 0
        for category_data in categories:
            category, created = ExpenseCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'color': category_data['color']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {len(categories)} categories. Created {created_count} new categories.')
        )
