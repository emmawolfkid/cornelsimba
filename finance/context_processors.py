# cornelsimba/finance/context_processors.py
from .models import Expense, Payroll
from django.db.models import Sum, F

def finance_context(request):
    """Make finance-related variables available in all templates"""
    if request.user.is_authenticated:
        # Only calculate for authenticated users
        unpaid_expense_count = Expense.objects.filter(is_paid=False).count()
        unpaid_payroll_count = Payroll.objects.filter(is_paid=False).count()
        
        # Calculate totals
        unpaid_expenses_total = Expense.objects.filter(is_paid=False).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        unpaid_payroll_total = Payroll.objects.filter(is_paid=False).aggregate(
            total=Sum(F('basic_salary') + F('allowances'))
        )['total'] or 0
        
        # Calculate pending counts for notification
        total_pending_count = unpaid_expense_count + unpaid_payroll_count
    else:
        unpaid_expense_count = 0
        unpaid_payroll_count = 0
        unpaid_expenses_total = 0
        unpaid_payroll_total = 0
        total_pending_count = 0
    
    return {
        'unpaid_expense_count': unpaid_expense_count,
        'unpaid_payroll_count': unpaid_payroll_count,
        'unpaid_expenses_total': unpaid_expenses_total,
        'unpaid_payroll_total': unpaid_payroll_total,
        'total_pending_count': total_pending_count,
    }