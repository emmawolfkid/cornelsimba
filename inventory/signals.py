# cornelsimba/inventory/signals.py (CREATE NEW FILE)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import StockOut
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=StockOut)
def handle_stockout_post_save(sender, instance, created, **kwargs):
    """
    Automatically create finance income when sale-related StockOut is approved
    """
    try:
        # Only process if: 1) Approved, 2) Sale-related, 3) Not already processed
        if (instance.status == 'approved' and 
            instance.purpose == 'SALE' and 
            instance.linked_sale and
            not instance.linked_sale.is_paid):  # Only if sale not already marked as paid
            
            # Import here to avoid circular imports
            from finance.models import Income
            
            # Check if income already exists for this sale
            income_exists = Income.objects.filter(
                reference=f"SALE_INCOME_{instance.linked_sale.sale_number}"
            ).exists()
            
            if not income_exists:
                with transaction.atomic():
                    # Create income record
                    income = Income.objects.create(
                        source=f"Sale: {instance.linked_sale.sale_number}",
                        amount=instance.linked_sale.net_amount,
                        date=instance.linked_sale.sale_date,
                        description=f"Sale to {instance.linked_sale.customer.name} - Stock Out #{instance.id}",
                        income_type='Sales',
                        department='Sales',
                        reference=f"SALE_INCOME_{instance.linked_sale.sale_number}",
                        created_at=instance.date
                    )
                    logger.info(f"Created income record #{income.id} for sale {instance.linked_sale.sale_number}")
                    
    except Exception as e:
        logger.error(f"Error in stockout finance integration: {str(e)}")
        # Don't raise exception to prevent save failure