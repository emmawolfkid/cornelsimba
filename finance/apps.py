# cornelsimba/finance/apps.py - UPDATED
from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    
    def ready(self):
        # Import signals
        import finance.signals