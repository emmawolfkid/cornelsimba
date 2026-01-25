from django.core.management.base import BaseCommand
from django.utils import timezone
from sales.models import Sale, SaleItem, Payment
from finance.models import Income, Expense, Payroll
import datetime

class Command(BaseCommand):
    help = 'Archive old sales and finance data older than 24 months'

    def handle(self, *args, **kwargs):
        cutoff_date = timezone.now().date() - datetime.timedelta(days=730)  # 24 months
        self.stdout.write(f"Archiving data older than {cutoff_date}")

        # Sales
        old_sales = Sale.objects.filter(sale_date__lt=cutoff_date)
        for sale in old_sales:
            sale.is_active = False
            sale.save(update_fields=['is_active'])
        
        # Sale items
        SaleItem.objects.filter(sale__sale_date__lt=cutoff_date).update(is_active=False)

        # Payments
        Payment.objects.filter(payment_date__lt=cutoff_date).update(is_active=False)

        # Finance
        Income.objects.filter(date__lt=cutoff_date).update(is_active=False)
        Expense.objects.filter(date__lt=cutoff_date).update(is_active=False)
        Payroll.objects.filter(year__lt=cutoff_date.year).update(is_active=False)

        self.stdout.write("Archiving complete")
