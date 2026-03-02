# finance/utils.py

def is_period_closed(target_date):
    from .models import AccountingPeriod

    return AccountingPeriod.objects.filter(
        year=target_date.year,
        month=target_date.month,
        is_closed=True
    ).exists()