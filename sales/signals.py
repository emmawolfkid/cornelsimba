# sales/signals.py - CREATE THIS
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale
from finance.models import Income

@receiver(post_save, sender=Sale)
def create_sale_income(sender, instance, created, **kwargs):
    """Auto-create income when sale is marked as COMPLETED"""
    if instance.status == 'COMPLETED' and not instance.income_records.exists():
        Income.create_from_sale(instance, None)