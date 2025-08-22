from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expenses'
    verbose_name = 'Expenses Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import expenses.signals
