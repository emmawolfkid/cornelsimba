from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = "Safely reset operational data (NO users, NO groups)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠ Resetting test data..."))

        with transaction.atomic():

            # ===== AUDIT =====
            try:
                from audit.models import AuditLog
                AuditLog.objects.all().delete()
                self.stdout.write("✔ Audit logs cleared")
            except Exception as e:
                self.stdout.write(f"Audit skipped: {e}")

            # ===== SALES =====
            try:
                from sales.models import SaleItem, Sale
                SaleItem.objects.all().delete()
                Sale.objects.all().delete()
                self.stdout.write("✔ Sales data cleared")
            except Exception as e:
                self.stdout.write(f"Sales skipped: {e}")

            # ===== INVENTORY (ORDER MATTERS) =====
            try:
                from inventory.models import (
                    StockHistory,
                    StockAdjustment,
                    StockOut,
                    StockIn,
                    Item,
                )

                StockHistory.objects.all().delete()
                StockAdjustment.objects.all().delete()
                StockOut.objects.all().delete()
                StockIn.objects.all().delete()
                Item.objects.all().delete()

                self.stdout.write("✔ Inventory cleared")
            except Exception as e:
                self.stdout.write(f"Inventory skipped: {e}")

            # ===== PROCUREMENT =====
            try:
                from procurement.models import PurchaseOrderItem, PurchaseOrder, Supplier
                PurchaseOrderItem.objects.all().delete()
                PurchaseOrder.objects.all().delete()
                Supplier.objects.all().delete()
                self.stdout.write("✔ Procurement cleared")
            except Exception as e:
                self.stdout.write(f"Procurement skipped: {e}")

            # ===== FINANCE =====
            try:
                from finance import models as finance_models

                for model_name in ["Payroll", "Expense", "LedgerEntry", "Payment", "Invoice"]:
                    model = getattr(finance_models, model_name, None)
                    if model:
                        model.objects.all().delete()

                self.stdout.write("✔ Finance cleared")
            except Exception as e:
                self.stdout.write(f"Finance skipped: {e}")

            # ===== HR =====
            try:
                from hr.models import LeaveRequest
                LeaveRequest.objects.all().delete()
                self.stdout.write("✔ HR leave data cleared")
            except Exception as e:
                self.stdout.write(f"HR skipped: {e}")

        self.stdout.write(self.style.SUCCESS("✅ Test data reset completed successfully"))
