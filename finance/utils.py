from .models import AccountingPeriod

def is_period_closed(date):
    return AccountingPeriod.objects.filter(
        start_date__lte=date,
        end_date__gte=date,
        is_closed=True
    ).exists()
