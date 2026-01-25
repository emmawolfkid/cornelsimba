# cornelsimba/finance/signals.py - NEW FILE
from django.db.models.signals import post_save
from django.dispatch import receiver
from inventory.models import StockOut
from sales.models import Sale
from .models import Income
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=StockOut)
def handle_stock_out_approval(sender, instance, created, **kwargs):
    """
    When stock out is approved, auto-create income record and mark sale as COMPLETED
    This connects Inventory -> Finance -> Sales completion
    """
    # Only process if stock out is approved, related to a sale, and is sale-related
    if (instance.status == 'approved' and 
        instance.is_sale_related and 
        instance.linked_sale):
        
        sale = instance.linked_sale
        
        # Check if income record already exists for this sale
        if not Income.objects.filter(sale=sale).exists():
            try:
                # Get user who approved the stock out
                user = instance.approved_by or User.objects.filter(is_superuser=True).first()
                
                # Auto-create income record from sale
                income = Income.create_from_sale(sale, user)
                
                # Mark sale as COMPLETED
                sale.status = 'COMPLETED'
                sale.stock_out_processed_date = instance.approved_at or instance.date
                sale.save(update_fields=['status', 'stock_out_processed_date', 'updated_at'])
                
                # Update sale items to mark as stocked out
                for sale_item in sale.items.all():
                    sale_item.is_stocked_out = True
                    sale_item.stock_out_date = instance.approved_at or instance.date
                    sale_item.save()
                
                print(f"✅ Auto-created income {income.id} from sale {sale.sale_number}")
                
            except Exception as e:
                print(f"❌ Error creating income from sale {sale.sale_number}: {e}")