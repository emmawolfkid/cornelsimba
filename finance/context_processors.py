# cornelsimba/finance/context_processors.py

from .models import FinanceEditRequest


def finance_context(request):
    """
    Global finance notification context.
    Provides unified approval count for Finance module.
    """

    if request.user.is_authenticated and request.user.is_superuser:
        finance_pending_requests = FinanceEditRequest.objects.filter(
            status='Pending'
        ).count()
    else:
        finance_pending_requests = 0

    return {
        'finance_pending_requests': finance_pending_requests,
    }