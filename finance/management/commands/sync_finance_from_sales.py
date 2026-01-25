# cornelsimba/finance/management/commands/sync_finance_from_sales.py - NEW FILE
from django.core.management.base import BaseCommand
from sales.models import Sale
from finance.models import Income
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync finance income records from completed sales'

    def handle(self, *args, **options):
        # Get all completed sales without income records
        completed_sales = Sale.objects.filter(
            status='COMPLETED',
            income_records__isnull=True
        )
        
        self.stdout.write(f"Found {completed_sales.count()} completed sales without income records")
        
        admin_user = User.objects.filter(is_superuser=True).first()
        
        for sale in completed_sales:
            try:
                # Check if sale has approved stock out
                if sale.inventory_stock_out and sale.inventory_stock_out.status == 'approved':
                    income = Income.create_from_sale(sale, admin_user)
                    self.stdout.write(
                        self.style.SUCCESS(f"Created income {income.id} for sale {sale.sale_number}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Sale {sale.sale_number} has no approved stock out")
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error for sale {sale.sale_number}: {e}")
                )