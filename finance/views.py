# cornelsimba/finance/views.py - COMPLETE FIXED VERSION
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from functools import wraps
from datetime import datetime, date
from .models import Income, Expense, Payroll, Account, Transaction
from .forms import IncomeForm, ExpenseForm, PayrollForm
from hr.models import Employee
from procurement.models import PurchaseOrder
from audit.utils import audit_log

from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from django.template.loader import get_template
from django.contrib.humanize.templatetags.humanize import intcomma
from .models import FinanceEditRequest
import logging 
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.utils import timezone
logger = logging.getLogger(__name__)


# Helper function to restrict access by group
def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('finance:dashboard')  # Fixed: Redirect to finance dashboard
        return _wrapped_view
    return decorator

# In finance/views.py - UPDATE the finance_dashboard function
@login_required
@group_required('Finance')
def finance_dashboard(request):
    """Finance Dashboard - COMPLETE VERSION with proper calculations"""
    # Current month/year
    current_month = date.today().strftime('%B')
    current_year = date.today().year
    today = date.today()
    
    # ========== INCOME CALCULATIONS ==========
    total_income = Income.objects.filter(is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    monthly_income = Income.objects.filter(
        date__month=today.month,
        date__year=today.year,
        is_active=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Cash income (only received money)
    cash_income = Income.objects.filter(is_paid=True, is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    unpaid_income = Income.objects.filter(is_paid=False, is_active=True).aggregate(total=Sum('amount'))['total'] or 0
    
    # Counts
    unpaid_income_count = Income.objects.filter(is_paid=False, is_active=True).count()
    total_income_count = Income.objects.filter(is_active=True).count()
    
    # ========== EXPENSE CALCULATIONS ==========
    total_expense = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    monthly_expense = Expense.objects.filter(
        date__month=today.month,
        date__year=today.year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Paid vs Unpaid expenses
    paid_expenses = Expense.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    unpaid_expenses = Expense.objects.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
    
    # Counts
    unpaid_expense_count = Expense.objects.filter(is_paid=False).count()
    paid_expense_count = Expense.objects.filter(is_paid=True).count()
    
    # ========== PAYROLL CALCULATIONS ==========
    payroll_count = Payroll.objects.count()
    
    # Current month payroll
    current_payroll = Payroll.objects.filter(
        month=current_month,
        year=current_year
    ).aggregate(
        total=Sum(F('basic_salary') + F('allowances'))
    )['total'] or 0
    
    # Total payroll liabilities (unpaid payroll)
    unpaid_payroll = Payroll.objects.filter(is_paid=False).aggregate(
        total=Sum(F('basic_salary') + F('allowances'))
    )['total'] or 0
    
    # Cash payroll (only paid payroll)
    paid_payroll = Payroll.objects.filter(is_paid=True).aggregate(
        total=Sum(F('basic_salary') + F('allowances'))
    )['total'] or 0
    
    # Counts
    unpaid_payroll_count = Payroll.objects.filter(is_paid=False).count()
    paid_payroll_count = Payroll.objects.filter(is_paid=True).count()
    
    # ========== FINANCIAL POSITION CALCULATIONS ==========
    
    # 1. CASH FLOW (Actual money available)
    available_cash = cash_income - paid_expenses - paid_payroll
    
    # 2. WORKING CAPITAL
    current_assets = cash_income + unpaid_income
    current_liabilities = unpaid_expenses + unpaid_payroll  # FIXED: This was missing
    working_capital = current_assets - current_liabilities
    
    # 3. FINANCIAL RATIOS
    current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else 0
    
    # 4. PROFIT/LOSS (Accrual basis)
    profit_loss = total_income - total_expense - current_payroll
    
    # 5. CASH PROFIT/LOSS (Cash basis)
    cash_profit_loss = cash_income - paid_expenses - paid_payroll
    
    # 6. CASH PROFIT MARGIN
    cash_profit_margin = 0
    if total_income > 0:
        cash_profit_margin = round((cash_profit_loss / total_income) * 100, 1)
    
    # ========== RECENT TRANSACTIONS ==========
    recent_incomes = Income.objects.filter(is_active=True).order_by('-date')[:5]
    recent_expenses = Expense.objects.all().order_by('-date')[:5]
    
    # ========== PENDING ITEMS ==========
    pending_pos = PurchaseOrder.objects.filter(status='Delivered').count()
    
    context = {
        # Basic stats
        'total_income': total_income,
        'monthly_income': monthly_income,
        'total_expense': total_expense,
        'monthly_expense': monthly_expense,
        'payroll_count': payroll_count,
        'current_payroll': current_payroll,
        'profit_loss': profit_loss,
        
        # Financial Position
        'available_cash': available_cash,
        'working_capital': working_capital,
        'current_liabilities': current_liabilities,  # ADDED: This was missing
        'current_ratio': round(current_ratio, 2),
        'cash_profit_loss': cash_profit_loss,
        'cash_profit_margin': cash_profit_margin,
        
        # Payable/Receivable
        'unpaid_expenses': unpaid_expenses,
        'unpaid_payroll': unpaid_payroll,
        'paid_expenses': paid_expenses,
        'paid_payroll': paid_payroll,
        'cash_income': cash_income,
        'unpaid_income': unpaid_income,
        
        # Counts for display
        'unpaid_expense_count': unpaid_expense_count,
        'unpaid_payroll_count': unpaid_payroll_count,
        'paid_expense_count': paid_expense_count,
        'paid_payroll_count': paid_payroll_count,
        'unpaid_income_count': unpaid_income_count,
        'total_income_count': total_income_count,
        
        # Recent & Pending
        'recent_incomes': recent_incomes,
        'recent_expenses': recent_expenses,
        'pending_pos': pending_pos,
        'current_month': current_month,
        'current_year': current_year,
        'today': today,
    }
    return render(request, 'finance/dashboard.html', context)
@login_required
@group_required('Finance')
def income_list(request):
    incomes = Income.objects.filter(is_active=True).order_by('-date')
    
    # Filters
    income_type = request.GET.get('type')
    year = request.GET.get('year')
    month = request.GET.get('month')
    search = request.GET.get('search')

    # Add filter to see cancelled if requested
    show_cancelled = request.GET.get('show_cancelled')
    if show_cancelled == 'true':
        incomes = Income.objects.all().order_by('-date')
    
    if income_type:
        incomes = incomes.filter(income_type=income_type)
    if year:
        incomes = incomes.filter(date__year=year)
    if month:
        incomes = incomes.filter(date__month=month)
    if search:
        incomes = incomes.filter(
            Q(source__icontains=search) |
            Q(reference__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Calculate totals directly
    total_amount = incomes.aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate quick stats
    paid_amount = incomes.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = incomes.filter(is_paid=False, is_cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
    cancelled_amount = incomes.filter(is_cancelled=True).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate average
    income_count = incomes.count()
    average_amount = total_amount / income_count if income_count > 0 else 0
    
    # Get distinct years for filter
    years = Income.objects.dates('date', 'year').distinct()
    
    context = {
        'incomes': incomes,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'cancelled_amount': cancelled_amount,
        'average_amount': average_amount,
        'income_types': Income.INCOME_TYPES,
        'years': years,
    }
    return render(request, 'finance/income_list.html', context)

# In finance/views.py - UPDATE income_create and income_edit
@login_required
@group_required('Finance')
def income_create(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.created_by = request.user.get_full_name() or request.user.username
            
            # Auto-set department if from sale
            if income.sale and not income.department:
                income.department = 'Sales'
            
            income.save()
            
            # Create transaction record
            try:
                from .models import Transaction, Account
                
                # Get or create sales income account
                sales_account, _ = Account.objects.get_or_create(
                    code='4000',
                    defaults={'name': 'Sales Revenue', 'account_type': 'Revenue'}
                )
                
                # Get or create cash account
                cash_account, _ = Account.objects.get_or_create(
                    code='1000',
                    defaults={'name': 'Cash', 'account_type': 'Asset'}
                )
                
                Transaction.objects.create(
                    transaction_type='Income',
                    amount=income.amount,
                    currency=income.currency,
                    description=f"Manual income entry: {income.source}",
                    income=income,
                    debit_account=cash_account,
                    credit_account=sales_account,
                    created_by=income.created_by
                )
            except Exception as e:
                print(f"Transaction creation failed: {e}")
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='FINANCE',
                object_type='Income',
                object_id=income.id,
                description=f'Created income: {income.source} - {income.amount_display}',
                request=request
            )
            
            messages.success(request, 
                f'Income record created: {income.source} - {income.amount_display}'
            )
            return redirect('finance:income_list')
    else:
        form = IncomeForm()
    
    return render(request, 'finance/income_form.html', {'form': form})

@login_required
@group_required('Finance')
def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            # Check if user is admin or has approval permission
            if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
                # Direct save for admins
                income = form.save()
                
                audit_log(
                    user=request.user,
                    action='UPDATE',
                    module='FINANCE',
                    object_type='Income',
                    object_id=income.id,
                    description=f'Updated income record: {income.source} - {income.amount_display}',
                    request=request
                )
                
                messages.success(request, 
                    f'Income record updated: {income.source} - {income.amount_display}'
                )
                return redirect('finance:income_list')
            else:
                # Create edit request for non-admins
                changes = {}

                for field, value in form.cleaned_data.items():
                    if isinstance(value, date):
                        changes[field] = value.strftime('%Y-%m-%d')
                    elif hasattr(value, 'pk'):
                        changes[field] = value.pk
                    else:
                        changes[field] = str(value) if value is not None else None
                
                # Create edit request (assuming you have this model)
                from .models import FinanceEditRequest
                FinanceEditRequest.objects.create(
                    request_type='Income',
                    object_id=income.id,
                    requested_changes=changes,
                    requested_by=request.user,
                    
                )
                
                messages.info(request, "Edit request submitted for admin approval.")
                return redirect('finance:income_list')
    else:
        form = IncomeForm(instance=income)
    
    return render(request, 'finance/income_form.html', {'form': form, 'editing': True})

# cornelsimba/finance/views.py - REPLACE income_delete WITH income_cancel
@login_required
@group_required('Finance')
def income_cancel(request, pk):
    """Cancel an income record instead of deleting it"""
    income = get_object_or_404(Income, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '').strip()
        
        if not reason:
            messages.error(request, 'Cancellation reason is required.')
            return redirect('finance:income_list')
        
        if income.is_cancelled:
            messages.warning(request, 'This income record is already cancelled.')
            return redirect('finance:income_list')
        
        # Cancel the income
        income.cancel(request.user, reason)
        
        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='DELETE',
            module='FINANCE',
            object_type='Income',
            object_id=income.id,
            description=f'Cancelled income: {income.source} - {income.amount_display}. Reason: {reason}',
            request=request
        )
        
        messages.warning(request, 
            f'Income record cancelled: {income.source} - {income.amount_display}. '
            f'Reason: {reason}'
        )
        return redirect('finance:income_list')
    
    return render(request, 'finance/income_cancel.html', {'income': income})
@login_required
@group_required('Finance')
def expense_list(request):
    expenses = Expense.objects.all().order_by('-date')
    
    # Filters
    expense_type = request.GET.get('type')
    department = request.GET.get('department')
    is_paid = request.GET.get('paid')
    search = request.GET.get('search')
    
    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)
    if department:
        expenses = expenses.filter(department=department)
    if is_paid:
        expenses = expenses.filter(is_paid=(is_paid == 'true'))
    if search:
        expenses = expenses.filter(
            Q(category__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Calculate totals for the filtered queryset
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    paid_amount = expenses.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = expenses.filter(is_paid=False).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate expense type totals
    procurement_amount = expenses.filter(expense_type='Procurement').aggregate(total=Sum('amount'))['total'] or 0
    salary_amount = expenses.filter(expense_type='Salary').aggregate(total=Sum('amount'))['total'] or 0
    utility_amount = expenses.filter(expense_type='Utility').aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate counts
    paid_expense_count = expenses.filter(is_paid=True).count()
    unpaid_expense_count = expenses.filter(is_paid=False).count()
    
    # Calculate percentages
    paid_percentage = (paid_amount / total_amount * 100) if total_amount > 0 else 0
    pending_percentage = (pending_amount / total_amount * 100) if total_amount > 0 else 0
    
    # Calculate average expense
    expense_count = expenses.count()
    average_amount = total_amount / expense_count if expense_count > 0 else 0
    
    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'procurement_amount': procurement_amount,  # ADD THIS
        'salary_amount': salary_amount,  # ADD THIS
        'utility_amount': utility_amount,  # ADD THIS
        'paid_expense_count': paid_expense_count,
        'unpaid_expense_count': unpaid_expense_count,
        'paid_percentage': round(paid_percentage, 1),
        'pending_percentage': round(pending_percentage, 1),
        'average_amount': average_amount,
        'expense_types': Expense.EXPENSE_TYPES,
    }
    return render(request, 'finance/expense_list.html', context)

@login_required
@group_required('Finance')
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            
            # Auto-set department if linked to PO
            if expense.purchase_order and not expense.department:
                expense.department = expense.purchase_order.department
            
            expense.save()
            
            # Create transaction record
            expense_account, _ = Account.objects.get_or_create(
                code='5000',
                defaults={'name': 'Operating Expenses', 'account_type': 'Expense'}
            )
            
            cash_account, _ = Account.objects.get_or_create(
                code='1000',
                defaults={'name': 'Cash', 'account_type': 'Asset'}
            )
            
            Transaction.objects.create(
                transaction_type='Expense',
                amount=expense.amount,
                currency=expense.currency,
                description=f"Expense payment: {expense.category}",
                expense=expense,
                debit_account=expense_account,
                credit_account=cash_account,
                created_by=request.user.get_full_name() or request.user.username
            )
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='FINANCE',
                object_type='Expense',
                object_id=expense.id,
                description=f'Created expense: {expense.category} - {expense.amount_display}',
                request=request
            )
            
            messages.success(request, 
                f'Expense record created: {expense.category} - {expense.amount_display}'
            )
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm()
    
    # IMPORTANT: Add expense_types to context
    context = {
        'form': form,
        'expense_types': Expense.EXPENSE_TYPES,  # Add this line
    }
    return render(request, 'finance/expense_form.html', context)
@login_required
@group_required('Finance')
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():

            if request.user.is_superuser:
                expense = form.save()

                audit_log(
                    user=request.user,
                    action='UPDATE',
                    module='FINANCE',
                    object_type='Expense',
                    object_id=expense.id,
                    description=f'Updated expense: {expense.category} - {expense.amount_display}',
                    request=request
                )

                messages.success(request,
                    f'Expense updated: {expense.category} - {expense.amount_display}'
                )
                return redirect('finance:expense_list')

            else:
                changes = {}

                for field, value in form.cleaned_data.items():
                    if isinstance(value, date):
                        changes[field] = value.strftime('%Y-%m-%d')
                    elif hasattr(value, 'pk'):
                        changes[field] = value.pk
                    else:
                        changes[field] = str(value) if value is not None else None

                FinanceEditRequest.objects.create(
                    request_type='Expense',
                    object_id=expense.id,
                    requested_changes=changes,
                    requested_by=request.user,
                )

                messages.info(request,
                    "Edit request submitted for admin approval."
                )
                return redirect('finance:expense_list')

    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'finance/expense_form.html', {
        'form': form,
        'editing': True
    })
@login_required
@group_required('Finance')
def expense_mark_paid(request, pk):

    expense = get_object_or_404(Expense, pk=pk)

    # 🔐 If NOT superuser → submit approval
    if not request.user.is_superuser:

        existing_request = FinanceEditRequest.objects.filter(
            request_type='Expense',
            object_id=expense.id,
            status='Pending'
        ).exists()

        if existing_request:
            messages.warning(request, "Approval request already pending.")
            return redirect('finance:expense_list')

        FinanceEditRequest.objects.create(
            request_type='Expense',
            object_id=expense.id,
            requested_changes={
                'is_paid': True,
                'payment_date': str(date.today())
            },
            requested_by=request.user
        )

        messages.info(request, "Expense payment request submitted for admin approval.")
        return redirect('finance:expense_list')

    # ✅ Superuser processes payment immediately
    if not expense.is_paid:
        expense.is_paid = True
        expense.payment_date = date.today()
        expense.save()

        audit_log(
            user=request.user,
            action='UPDATE',
            module='FINANCE',
            object_type='Expense',
            object_id=expense.id,
            description=f'Marked expense as paid: {expense.category} - {expense.amount_display}',
            request=request
        )

        messages.success(request,
            f'Expense marked as paid: {expense.category} - {expense.amount_display}'
        )

    return redirect('finance:expense_list')

@login_required
@group_required('Finance')
def payroll_list(request):
    payrolls = Payroll.objects.select_related('employee').all().order_by('-year', '-month')
    
    # Filters
    year = request.GET.get('year')
    month = request.GET.get('month')
    is_paid = request.GET.get('paid')
    
    if year:
        payrolls = payrolls.filter(year=year)
    if month:
        payrolls = payrolls.filter(month=month)
    if is_paid:
        payrolls = payrolls.filter(is_paid=(is_paid == 'true'))
    
    # Summary
    total_net = payrolls.aggregate(
        total=Sum(
            F('basic_salary') + F('allowances') - F('deductions') - 
            F('tax_amount') - F('pension_amount') - F('other_deductions')
        )
    )['total'] or 0
    
    total_gross = payrolls.aggregate(
        total=Sum(F('basic_salary') + F('allowances'))
    )['total'] or 0
    
    context = {
        'payrolls': payrolls,
        'total_net': total_net,
        'total_gross': total_gross,
        'years': Payroll.objects.values_list('year', flat=True).distinct().order_by('-year'),
        'months': Payroll.MONTH_CHOICES,
    }
    return render(request, 'finance/payroll_list.html', context)


@login_required
@group_required('Finance')
def payroll_create(request):
    if request.method == 'POST':
        form = PayrollForm(request.POST)
        if form.is_valid():
            payroll = form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='FINANCE',
                object_type='Payroll',
                object_id=payroll.id,
                description=f'Created payroll for {payroll.employee.full_name} - {payroll.net_salary_display}',
                request=request
            )
            
            messages.success(request, 
                f'Payroll created for {payroll.employee.full_name} - {payroll.net_salary_display}'
            )
            return redirect('finance:payroll_list')
    else:
        form = PayrollForm()
    
    return render(request, 'finance/payroll_form.html', {'form': form})

@login_required
@group_required('Finance')
def payroll_mark_paid(request, pk):

    payroll = get_object_or_404(Payroll, pk=pk)

    # 🔐 If NOT superuser → submit approval request
    if not request.user.is_superuser:

        # Prevent duplicate requests
        existing_request = FinanceEditRequest.objects.filter(
            request_type='Payroll',
            object_id=payroll.id,
            status='Pending'
        ).exists()

        if existing_request:
            messages.warning(request, "Approval request already pending.")
            return redirect('finance:payroll_list')

        FinanceEditRequest.objects.create(
            request_type='Payroll',
            object_id=payroll.id,
            requested_changes={
                'is_paid': True,
                'payment_date': str(date.today())
            },
            requested_by=request.user
        )

        messages.info(request, "Payroll payment request submitted for admin approval.")
        return redirect('finance:payroll_list')

    # ✅ Superuser processes payment immediately
    if not payroll.is_paid:
        payroll.is_paid = True
        payroll.payment_date = date.today()
        payroll.save()

        salary_expense_account, _ = Account.objects.get_or_create(
            code='5100',
            defaults={'name': 'Salary Expense', 'account_type': 'Expense'}
        )

        cash_account, _ = Account.objects.get_or_create(
            code='1000',
            defaults={'name': 'Cash', 'account_type': 'Asset'}
        )

        Transaction.objects.create(
            transaction_type='Payroll',
            amount=payroll.basic_salary + payroll.allowances,
            currency=payroll.currency,
            description=f"Payroll payment: {payroll.employee.full_name}",
            payroll=payroll,
            debit_account=salary_expense_account,
            credit_account=cash_account,
            created_by=request.user.get_full_name() or request.user.username
        )

        audit_log(
            user=request.user,
            action='UPDATE',
            module='FINANCE',
            object_type='Payroll',
            object_id=payroll.id,
            description=f'Marked payroll as paid for {payroll.employee.full_name} - {payroll.net_salary_display}',
            request=request
        )

        messages.success(
            request,
            f'Payroll marked as paid for {payroll.employee.full_name} - {payroll.net_salary_display}'
        )

    return redirect('finance:payroll_list')

@login_required
@group_required('Finance')
def download_payroll_pdf(request, pk):

    payroll = get_object_or_404(Payroll, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payroll_{pk}.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Payroll Slip", styles['Heading2']))
    elements.append(Spacer(1, 0.3 * inch))

    net_salary = payroll.net_salary()

    data = [
        ["Employee", payroll.employee.full_name],
        ["Month", f"{payroll.month} {payroll.year}"],
        ["Basic Salary", f"{payroll.basic_salary:,.2f}"],
        ["Allowances", f"{payroll.allowances:,.2f}"],
        ["Deductions", f"{payroll.deductions:,.2f}"],
        ["Net Salary", f"{net_salary:,.2f}"],
        ["Status", "PAID" if payroll.is_paid else "UNPAID"],
    ]

    table = Table(data, colWidths=[2.5 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

@login_required
@group_required('Finance')
def procurement_expenses(request):
    """View delivered POs that can be converted to expenses"""
    delivered_pos = PurchaseOrder.objects.filter(status='Delivered').select_related(
        'supplier', 'requested_by'
    ).order_by('-order_date')
    
    # Check which POs already have expenses
    for po in delivered_pos:
        po.has_expense = po.expenses.exists()
    
    # Department summary
    department_summary = {}
    for po in delivered_pos:
        dept = po.department or 'Unknown'
        if dept not in department_summary:
            department_summary[dept] = {'count': 0, 'total': 0}
        department_summary[dept]['count'] += 1
        department_summary[dept]['total'] += float(po.total_amount)
    
    context = {
        'purchase_orders': delivered_pos,
        'department_summary': department_summary,
        'total_value': sum(po.total_amount for po in delivered_pos),
    }
    return render(request, 'finance/procurement_expenses.html', context)


@login_required
@group_required('Finance')
@transaction.atomic
def create_expense_from_po(request, po_id):
    """Convert a Purchase Order to an Expense"""
    purchase_order = get_object_or_404(PurchaseOrder, id=po_id)
    
    # Check if expense already exists
    if purchase_order.expenses.exists():
        messages.warning(request, f'Expense already exists for PO {purchase_order.po_number}')
        return redirect('finance:procurement_expenses')
    
    # Create expense from PO
    expense = Expense.objects.create(
        category=f"PO: {purchase_order.supplier.name}",
        expense_type='Procurement',
        amount=purchase_order.total_amount,
        currency='Tsh',  # Always Tsh for procurement
        date=date.today(),
        description=f"Purchase Order {purchase_order.po_number}\nItems: {', '.join([item.item.name for item in purchase_order.items.all()])}",
        purchase_order=purchase_order,
        department=purchase_order.department,
        is_paid=False,
        payment_method='Bank'
    )
    
    # 🔴 AUDIT ADD - After this line
    audit_log(
        user=request.user,
        action='CREATE',
        module='FINANCE',
        object_type='Expense',
        object_id=expense.id,
        description=f'Created expense from PO {purchase_order.po_number} - Tsh {purchase_order.total_amount:,.2f}',
        request=request
    )
    
    messages.success(request, 
        f'Expense created from PO {purchase_order.po_number} for Tsh {purchase_order.total_amount:,.2f}'
    )
    return redirect('finance:expense_list')

@login_required
@group_required('Finance')
def financial_reports(request):

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    year = request.GET.get('year')

    # Determine reporting period
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        period_label = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"

    elif year:
        year = int(year)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        period_label = f"January {year} - December {year}"

    else:
        current_year = date.today().year
        start_date = date(current_year, 1, 1)
        end_date = date.today()
        period_label = f"January {current_year} - {end_date.strftime('%B %d, %Y')}"

    # ======= MAIN CALCULATIONS =======
    total_income = Income.objects.filter(
        date__range=[start_date, end_date],
        is_active=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_expense = Expense.objects.filter(
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    profit_loss = total_income - total_expense
    profit_margin = (profit_loss / total_income * 100) if total_income > 0 else 0

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'total_income': total_income,
        'total_expense': total_expense,
        'profit_loss': profit_loss,
        'profit_margin': round(profit_margin, 1),
    }

    return render(request, 'finance/reports.html', context)

@login_required
@group_required('Finance')
def download_financial_report_pdf(request):

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    year = request.GET.get('year')

    if start_date and end_date:

        # Parse start_date safely
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                try:
                    start_date = datetime.strptime(start_date, '%b. %d, %Y').date()
                except ValueError:
                    start_date = datetime.strptime(start_date, '%B %d, %Y').date()

        # Parse end_date safely
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                try:
                    end_date = datetime.strptime(end_date, '%b. %d, %Y').date()
                except ValueError:
                    end_date = datetime.strptime(end_date, '%B %d, %Y').date()

        period_label = f"{start_date} to {end_date}"

    elif year:
        year = int(year)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        period_label = f"Year {year}"

    else:
        current_year = date.today().year
        start_date = date(current_year, 1, 1)
        end_date = date.today()
        period_label = f"{start_date} to {end_date}"

    total_income = Income.objects.filter(
        date__range=[start_date, end_date],
        is_active=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_expense = Expense.objects.filter(
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    profit_loss = total_income - total_expense
    profit_margin = (profit_loss / total_income * 100) if total_income > 0 else 0

    # ======== PDF =========
    response = HttpResponse(content_type='application/pdf')
    filename = f"financial_report_{start_date}_to_{end_date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Financial Report", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"Period: {period_label}", styles['Normal']))
    elements.append(Spacer(1, 0.4 * inch))

    data = [
        ["Category", "Amount (Tsh)"],
        ["Total Income", f"{total_income:,.2f}"],
        ["Total Expense", f"{total_expense:,.2f}"],
        ["Profit / Loss", f"{profit_loss:,.2f}"],
        ["Profit Margin (%)", f"{profit_margin:.1f}%"],
    ]

    table = Table(data, colWidths=[3 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

@login_required
@group_required('Finance')
def income_mark_paid(request, pk):

    income = get_object_or_404(Income, pk=pk)

    # 🔐 If NOT superuser → submit approval
    if not request.user.is_superuser:

        existing_request = FinanceEditRequest.objects.filter(
            request_type='Income',
            object_id=income.id,
            status='Pending'
        ).exists()

        if existing_request:
            messages.warning(request, "Approval request already pending.")
            return redirect('finance:income_list')

        FinanceEditRequest.objects.create(
            request_type='Income',
            object_id=income.id,
            requested_changes={
                'is_paid': True,
                'payment_date': str(date.today())
            },
            requested_by=request.user
        )

        messages.info(request, "Income payment request submitted for admin approval.")
        return redirect('finance:income_list')

    # ✅ Superuser processes payment
    if not income.is_paid:
        income.is_paid = True
        income.payment_date = date.today()
        income.save()

        audit_log(
            user=request.user,
            action='UPDATE',
            module='FINANCE',
            object_type='Income',
            object_id=income.id,
            description=f'Marked income as paid: {income.source} - {income.amount_display}',
            request=request
        )

        messages.success(request,
            f'Income marked as paid: {income.source} - {income.amount_display}'
        )

    return redirect('finance:income_list')

@login_required
@group_required('Finance')
def cash_flow_statement(request):
    """Generate Cash Flow Statement (Operating Activities)"""

    # ========= DATE RANGE =========
    end_date = date.today()
    start_date = end_date.replace(day=1)

    if request.GET.get('start_date'):
        start_date = datetime.strptime(
            request.GET.get('start_date'), '%Y-%m-%d'
        ).date()

    if request.GET.get('end_date'):
        end_date = datetime.strptime(
            request.GET.get('end_date'), '%Y-%m-%d'
        ).date()

    # ========= CASH INFLOWS =========
    cash_inflows = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ========= CASH OUTFLOWS =========
    cash_outflows = Expense.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    payroll_outflows = Payroll.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(
        total=Sum(F('basic_salary') + F('allowances'))
    )['total'] or 0

    total_outflows = cash_outflows + payroll_outflows
    net_cash_flow = cash_inflows - total_outflows

    # ========= ACCRUAL INCOME (FOR CONVERSION RATE) =========
    total_income = Income.objects.filter(
        is_active=True,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ========= ANALYTICS =========
    if total_income > 0:
        cash_conversion_rate = round(
            (cash_inflows / total_income) * 100, 1
        )
    else:
        cash_conversion_rate = 0

    if total_outflows > 0:
        cash_reserve_coverage = round(
            (net_cash_flow / total_outflows), 1
        )
    else:
        cash_reserve_coverage = 0

    # ========= TRANSACTION DETAILS =========
    income_transactions = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]

    expense_transactions = Expense.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]

    payroll_transactions = Payroll.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'cash_inflows': cash_inflows,
        'cash_outflows': cash_outflows,
        'payroll_outflows': payroll_outflows,
        'total_outflows': total_outflows,
        'net_cash_flow': net_cash_flow,
        'total_income': total_income,
        'cash_conversion_rate': cash_conversion_rate,
        'cash_reserve_coverage': cash_reserve_coverage,
        'income_transactions': income_transactions,
        'expense_transactions': expense_transactions,
        'payroll_transactions': payroll_transactions,
    }

    return render(request, 'finance/cash_flow.html', context)

@login_required
@group_required('Finance')
def general_ledger(request):
    """Generate general ledger with all transactions - SIMPLIFIED"""
    # Get date range (default to current month)
    end_date = date.today()
    start_date = end_date.replace(day=1)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Get all transactions in date range
    transactions = Transaction.objects.filter(
        date__date__range=[start_date, end_date]
    ).select_related('debit_account', 'credit_account').order_by('-date')
    
    # Calculate totals
    debit_total = 0
    credit_total = 0
    
    for transaction in transactions:
        debit_total += transaction.amount
        credit_total += transaction.amount
    
    # Calculate account summaries
    accounts_summary = {}
    for transaction in transactions:
        # Debit account
        debit_acc_code = transaction.debit_account.code
        if debit_acc_code not in accounts_summary:
            accounts_summary[debit_acc_code] = {
                'account': transaction.debit_account,
                'debits': 0,
                'credits': 0,
            }
        accounts_summary[debit_acc_code]['debits'] += transaction.amount
        
        # Credit account
        credit_acc_code = transaction.credit_account.code
        if credit_acc_code not in accounts_summary:
            accounts_summary[credit_acc_code] = {
                'account': transaction.credit_account,
                'debits': 0,
                'credits': 0,
            }
        accounts_summary[credit_acc_code]['credits'] += transaction.amount
    
    balance_difference = abs(debit_total - credit_total)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'transactions': transactions,
        'accounts_summary': accounts_summary,
        'debit_total': debit_total,
        'credit_total': credit_total,
        'balance_difference': balance_difference,
    }
    return render(request, 'finance/general_ledger.html', context)
    
@login_required
@group_required('Finance')
def expense_detail(request, pk):
    """View detailed expense information"""
    expense = get_object_or_404(Expense, pk=pk)
    
    # Get related transactions
    related_transactions = Transaction.objects.filter(expense=expense)
    
    context = {
        'expense': expense,
        'related_transactions': related_transactions,
    }
    return render(request, 'finance/expense_detail.html', context)
@login_required
@group_required('Finance')
def download_expense_pdf(request, pk):

    expense = get_object_or_404(Expense, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expense_{expense.id}.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Expense Report", styles['Heading2']))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Category", expense.category],
        ["Type", expense.expense_type],
        ["Amount", f"{expense.amount:,.2f} {expense.currency}"],
        ["Date", expense.date.strftime('%B %d, %Y')],
        ["Status", "PAID" if expense.is_paid else "UNPAID"],
    ]

    table = Table(data, colWidths=[2.5 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)

    doc.build(elements)
    return response

@login_required
@group_required('Finance')
def process_payroll_with_leaves(request):
    """Process payroll including leave deductions"""
    from hr.models import LeaveRequest  # Import here to avoid circular imports
    
    # Get current month/year
    current_month = date.today().strftime('%B')
    current_year = date.today().year
    
    # Get all active employees
    employees = Employee.objects.filter(is_active=True)
    
    payroll_processed = []
    
    for employee in employees:
        # Calculate leave deductions for unpaid leaves
        leave_deductions = 0
        
        # Get approved unpaid leaves for current month
        unpaid_leaves = LeaveRequest.objects.filter(
            employee=employee,
            status='approved',
            payroll_processed=False,
            start_date__month=date.today().month,
            start_date__year=date.today().year
        )
        
        # Calculate deduction for each unpaid leave
        for leave in unpaid_leaves:
            # Skip paid leaves (annual, sick, etc.)
            if getattr(leave, 'is_paid_leave', False):
                continue
                
            # Get employee salary from last payroll or employee record
            last_payroll = Payroll.objects.filter(employee=employee).order_by('-year', '-month').first()
            if last_payroll:
                daily_rate = last_payroll.basic_salary / 22
                leave_deductions += daily_rate * leave.days_requested
                
                # Mark as processed
                leave.payroll_processed = True
                leave.save()
        
        # Get employee's basic salary
        # First try from last payroll
        last_payroll = Payroll.objects.filter(employee=employee).order_by('-year', '-month').first()
        if last_payroll:
            basic_salary = last_payroll.basic_salary
        else:
            # Try from employee attributes
            if hasattr(employee, 'salary') and employee.salary:
                basic_salary = employee.salary
            elif hasattr(employee, 'monthly_salary') and employee.monthly_salary:
                basic_salary = employee.monthly_salary
            else:
                continue  # Skip employees without salary information
        
        # Create or update payroll
        payroll, created = Payroll.objects.get_or_create(
            employee=employee,
            month=current_month,
            year=current_year,
            defaults={
                'basic_salary': basic_salary,
                'deductions': leave_deductions,
                'tax_amount': 0,  # You might want to calculate these
                'pension_amount': 0,
                'other_deductions': 0,
                'leave_deductions': leave_deductions,  # Store leave deductions separately
            }
        )
        
        if not created:
            # Update existing payroll
            payroll.leave_deductions = leave_deductions
            payroll.deductions = payroll.tax_amount + payroll.pension_amount + payroll.other_deductions + leave_deductions
            payroll.save()
        
        payroll_processed.append(payroll)
    
    messages.success(request, f'Payroll processed for {len(payroll_processed)} employees including leave deductions')
    return redirect('finance:payroll_list')

@login_required
@group_required('Finance')
def trial_balance(request):
    """Generate trial balance report - SIMPLIFIED VERSION"""
    # Get all active accounts
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    total_debits = 0
    total_credits = 0
    
    # Prepare account data
    account_data = []
    for account in accounts:
        # Get all debit and credit transactions for this account
        debit_total = account.debit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        credit_total = account.credit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Determine normal balance based on account type
        if account.account_type in ['Asset', 'Expense']:
            debit_balance = max(debit_total - credit_total, 0)
            credit_balance = max(credit_total - debit_total, 0)
        else:
            credit_balance = max(credit_total - debit_total, 0)
            debit_balance = max(debit_total - credit_total, 0)

        is_debit = debit_total >= credit_total

        # Add calculated values to account object
        account.debit_balance = debit_balance
        account.credit_balance = credit_balance
        account.is_debit = is_debit
        
        total_debits += debit_balance
        total_credits += credit_balance
        
        account_data.append(account)
    
    # Check if trial balance is balanced (allow for small rounding)
    is_balanced = abs(total_debits - total_credits) < 1  # Less than 1 Tsh difference
    
    context = {
        'accounts': account_data,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'difference': total_debits - total_credits,
        'abs_difference': abs(total_debits - total_credits),
        'is_balanced': is_balanced,
        'date': date.today(),
    }
    
    return render(request, 'finance/trial_balance.html', context)

@login_required
@group_required('Finance')
def income_statement(request):

    # ========= GET DATE FILTERS =========
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = None
        end_date = None

    # ========= GET ACCOUNTS =========
    revenues = Account.objects.filter(account_type='Revenue')
    expenses = Account.objects.filter(account_type='Expense')

    revenue_data = []
    expense_data = []

    total_revenue = 0
    total_expense = 0

    # ========= REVENUES =========
    for acc in revenues:
        transactions = acc.credit_transactions.all()

        if start_date and end_date:
            transactions = transactions.filter(
                date__range=[start_date, end_date]
            )

        amount = transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        if amount > 0:
            revenue_data.append({
                'account': acc,
                'amount': amount
            })
            total_revenue += amount

    # ========= EXPENSES =========
    for acc in expenses:
        transactions = acc.debit_transactions.all()

        if start_date and end_date:
            transactions = transactions.filter(
                date__range=[start_date, end_date]
            )

        amount = transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        if amount > 0:
            expense_data.append({
                'account': acc,
                'amount': amount
            })
            total_expense += amount

    net_profit = total_revenue - total_expense

    return render(request, 'finance/income_statement.html', {
        'revenue_data': revenue_data,
        'expense_data': expense_data,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'start_date': start_date,
        'end_date': end_date,
    })

@login_required
@group_required('Finance')
def balance_sheet(request):
    """Balance Sheet"""
    assets = Account.objects.filter(account_type='Asset')
    liabilities = Account.objects.filter(account_type='Liability')
    equity = Account.objects.filter(account_type='Equity')

    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for acc in assets:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_assets += (debits - credits)

    for acc in liabilities:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_liabilities += (credits - debits)

    for acc in equity:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_equity += (credits - debits)

    # FIXED: Return statement is now properly outside all loops
    return render(request, 'finance/balance_sheet.html', {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 1
    })
    
@login_required
@group_required('Finance')
def download_general_ledger_pdf(request):

    end_date = date.today()
    start_date = end_date.replace(day=1)

    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()

    transactions = Transaction.objects.filter(
        date__date__range=[start_date, end_date]
    ).select_related('debit_account', 'credit_account').order_by('-date')

    debit_total = 0
    credit_total = 0

    rows = []

    for t in transactions:
        debit_total += t.amount
        credit_total += t.amount

        rows.append([
            t.date.strftime("%Y-%m-%d"),
            t.debit_account.name,
            f"{t.amount:,.2f}",
            t.credit_account.name,
            f"{t.amount:,.2f}",
        ])

    balance_difference = abs(debit_total - credit_total)

    # ================= PDF =================

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="general_ledger_{start_date}_to_{end_date}.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("General Ledger", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(
        f"Period: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Date", "Debit Account", "Debit (Tsh)", "Credit Account", "Credit (Tsh)"]
    ]

    data += rows

    data.append([
        "",
        "TOTAL",
        f"{debit_total:,.2f}",
        "",
        f"{credit_total:,.2f}"
    ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    status_text = "BALANCED ✅" if balance_difference == 0 else f"NOT BALANCED ❌ (Difference: {balance_difference:,.2f})"

    elements.append(Paragraph(status_text, styles['Normal']))

    doc.build(elements)
    return response


@login_required
@group_required('Finance')
def download_trial_balance_pdf(request):

    accounts = Account.objects.filter(is_active=True).order_by('code')

    total_debits = 0
    total_credits = 0

    account_rows = []

    for account in accounts:

        debit_total = account.debit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        credit_total = account.credit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        if account.account_type in ['Asset', 'Expense']:
            debit_balance = max(debit_total - credit_total, 0)
            credit_balance = max(credit_total - debit_total, 0)
        else:
            credit_balance = max(credit_total - debit_total, 0)
            debit_balance = max(debit_total - credit_total, 0)

        if debit_balance > 0:
            total_debits += debit_balance
        if credit_balance > 0:
            total_credits += credit_balance

        account_rows.append([
            account.code,
            account.name,
            account.account_type,
            f"{debit_balance:,.2f}" if debit_balance > 0 else "-",
            f"{credit_balance:,.2f}" if credit_balance > 0 else "-"
        ])

    is_balanced = abs(total_debits - total_credits) < 1

    # ================= PDF =================

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="trial_balance.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Trial Balance", styles['Heading2']))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Code", "Account", "Type", "Debit (Tsh)", "Credit (Tsh)"]
    ]

    data += account_rows

    data.append([
        "",
        "TOTAL",
        "",
        f"{total_debits:,.2f}",
        f"{total_credits:,.2f}"
    ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    status_text = "BALANCED ✅" if is_balanced else "NOT BALANCED ❌"

    elements.append(Paragraph(
        f"Status: {status_text}",
        styles['Normal']
    ))

    doc.build(elements)
    return response
        
@login_required
@group_required('Finance')
def download_income_statement_pdf(request):
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')

    start_date = None
    end_date = None

    if start_date_param and end_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
            end_date = None

    revenues = Account.objects.filter(account_type='Revenue')
    expenses = Account.objects.filter(account_type='Expense')

    total_revenue = 0
    total_expense = 0

    revenue_details = []
    expense_details = []

    # ========= REVENUES =========
    for acc in revenues:
        transactions = acc.credit_transactions.all()

        if start_date and end_date:
            transactions = transactions.filter(
                date__range=[start_date, end_date]
            )

        revenue_amount = transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        if revenue_amount > 0:
            revenue_details.append((acc.name, revenue_amount))
            total_revenue += revenue_amount

    # ========= EXPENSES =========
    for acc in expenses:
        transactions = acc.debit_transactions.all()

        if start_date and end_date:
            transactions = transactions.filter(
                date__range=[start_date, end_date]
            )

        expense_amount = transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

        if expense_amount > 0:
            expense_details.append((acc.name, expense_amount))
            total_expense += expense_amount

    net_profit = total_revenue - total_expense

    # ========== PDF ==========
    response = HttpResponse(content_type='application/pdf')
    filename = f"income_statement_{start_date or 'all'}_to_{end_date or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Income Statement", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))

    if start_date and end_date:
        elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

    # Revenue table
    revenue_data = [["Account", "Amount (Tsh)"]]
    for name, amount in revenue_details:
        revenue_data.append([name, f"{amount:,.2f}"])
    revenue_data.append(["Total Revenue", f"{total_revenue:,.2f}"])

    revenue_table = Table(revenue_data, colWidths=[3 * inch, 2 * inch])
    revenue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(revenue_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Expense table
    expense_data = [["Account", "Amount (Tsh)"]]
    for name, amount in expense_details:
        expense_data.append([name, f"{amount:,.2f}"])
    expense_data.append(["Total Expenses", f"{total_expense:,.2f}"])

    expense_table = Table(expense_data, colWidths=[3 * inch, 2 * inch])
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(expense_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"Net Profit / Loss: {net_profit:,.2f} Tsh",
        styles['Heading3']
    ))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%B %d, %Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)
    return response

@login_required
@group_required('Finance')
def download_cash_flow_pdf(request):

    end_date = date.today()
    start_date = end_date.replace(day=1)

    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()

    # Calculations (same as cash_flow_statement view)

    cash_inflows = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    cash_outflows = Expense.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    payroll_outflows = Payroll.objects.filter(
        is_paid=True,
        payment_date__isnull=False,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum(F('basic_salary') + F('allowances')))['total'] or 0

    total_outflows = cash_outflows + payroll_outflows
    net_cash_flow = cash_inflows - total_outflows

    # ================= PDF =================

    response = HttpResponse(content_type='application/pdf')
    filename = f"cash_flow_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Cash Flow Statement", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(
        f"Period: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.4 * inch))

    data = [
        ["Category", "Amount (Tsh)"],
        ["Cash Inflows", f"{cash_inflows:,.0f}"],
        ["Expense Outflows", f"{cash_outflows:,.0f}"],
        ["Payroll Outflows", f"{payroll_outflows:,.0f}"],
        ["Total Outflows", f"{total_outflows:,.0f}"],
        ["Net Cash Flow", f"{net_cash_flow:,.0f}"],
]

    table = Table(data, colWidths=[3 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.4 * inch))

    if net_cash_flow >= 0:
        status_text = "POSITIVE CASH FLOW ✅"
    else:
        status_text = "NEGATIVE CASH FLOW ❌"

    elements.append(Paragraph(status_text, styles['Normal']))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%B %d, %Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)
    return response




@login_required
@group_required('Finance')
def download_balance_sheet_pdf(request):

    # ===============================
    # SAME LOGIC AS YOUR balance_sheet VIEW
    # ===============================

    assets = Account.objects.filter(account_type='Asset')
    liabilities = Account.objects.filter(account_type='Liability')
    equity_accounts = Account.objects.filter(account_type='Equity')

    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    # Calculate Assets
    for acc in assets:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_assets += (debits - credits)

    # Calculate Liabilities
    for acc in liabilities:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_liabilities += (credits - debits)

    # Calculate Equity
    for acc in equity_accounts:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        total_equity += (credits - debits)

    # ===============================
    # CREATE PDF
    # ===============================

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="balance_sheet.pdf"'

    doc = SimpleDocTemplate(response)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Cornel Simba Mining Enterprise", styles['Heading1']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Balance Sheet", styles['Heading2']))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Category", "Amount (Tsh)"],
        ["Total Assets", f"{total_assets:,.2f}"],
        ["Total Liabilities", f"{total_liabilities:,.2f}"],
        ["Total Equity", f"{total_equity:,.2f}"],
    ]

    table = Table(data, colWidths=[3 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.4 * inch))

    is_balanced = abs(total_assets - (total_liabilities + total_equity)) < 1

    status_text = "BALANCED ✅" if is_balanced else "NOT BALANCED ❌"

    elements.append(Paragraph(
        f"Status: {status_text}",
        styles['Normal']
    ))

    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"Generated on: {timezone.now().strftime('%B %d, %Y %H:%M')}",
        styles['Normal']
    ))

    doc.build(elements)
    return response

@login_required
def pending_finance_edits(request):

    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('finance:dashboard')

    pending_requests = FinanceEditRequest.objects.filter(
        status='Pending'
    ).order_by('-created_at')

    return render(request, 'finance/pending_edits.html', {
        'pending_requests': pending_requests
    })

@login_required
@transaction.atomic
def approve_finance_edit(request, pk):

    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('finance:dashboard')

    edit_request = get_object_or_404(FinanceEditRequest, pk=pk)

    if edit_request.status != 'Pending':
        messages.warning(request, "Request already processed.")
        return redirect('finance:pending_finance_edits')

    # ==========================
    # Get Target Object
    # ==========================
    if edit_request.request_type == 'Income':
        obj = get_object_or_404(Income, pk=edit_request.object_id)

    elif edit_request.request_type == 'Expense':
        obj = get_object_or_404(Expense, pk=edit_request.object_id)

    elif edit_request.request_type == 'Payroll':
        obj = get_object_or_404(Payroll, pk=edit_request.object_id)

    else:
        messages.error(request, "Invalid request type.")
        return redirect('finance:pending_finance_edits')

    # ==========================
    # Apply Requested Changes
    # ==========================
    for field, value in edit_request.requested_changes.items():

        if field == 'payment_date' and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()

        setattr(obj, field, value)

    obj.save()
    # ADD THIS BLOCK
    if edit_request.request_type in ['Expense', 'Payroll', 'Income']:
        obj.approved_by = request.user
        obj.save(update_fields=['approved_by'])

    # ==========================
    # CREATE ACCOUNTING TRANSACTION (IF PAYMENT APPROVAL)
    # ==========================
    if 'is_paid' in edit_request.requested_changes:

        # -------- EXPENSE PAYMENT --------
        if edit_request.request_type == 'Expense':

            expense_account, _ = Account.objects.get_or_create(
                code='5000',
                defaults={'name': 'Operating Expenses', 'account_type': 'Expense'}
            )

            cash_account, _ = Account.objects.get_or_create(
                code='1000',
                defaults={'name': 'Cash', 'account_type': 'Asset'}
            )

            Transaction.objects.create(
                transaction_type='Expense',
                amount=obj.amount,
                currency=obj.currency,
                description=f"Approved expense payment: {obj.category}",
                expense=obj,
                debit_account=expense_account,
                credit_account=cash_account,
                created_by=request.user.get_full_name() or request.user.username
            )

        # -------- PAYROLL PAYMENT --------
        elif edit_request.request_type == 'Payroll':

            salary_account, _ = Account.objects.get_or_create(
                code='5100',
                defaults={'name': 'Salary Expense', 'account_type': 'Expense'}
            )

            cash_account, _ = Account.objects.get_or_create(
                code='1000',
                defaults={'name': 'Cash', 'account_type': 'Asset'}
            )

            Transaction.objects.create(
                transaction_type='Payroll',
                amount=obj.basic_salary + obj.allowances,
                currency=obj.currency,
                description=f"Approved payroll payment: {obj.employee.full_name}",
                payroll=obj,
                debit_account=salary_account,
                credit_account=cash_account,
                created_by=request.user.get_full_name() or request.user.username
            )

        # -------- INCOME PAYMENT --------
        elif edit_request.request_type == 'Income':

            cash_account, _ = Account.objects.get_or_create(
                code='1000',
                defaults={'name': 'Cash', 'account_type': 'Asset'}
            )

            revenue_account, _ = Account.objects.get_or_create(
                code='4000',
                defaults={'name': 'Sales Revenue', 'account_type': 'Revenue'}
            )

            Transaction.objects.create(
                transaction_type='Income',
                amount=obj.amount,
                currency=obj.currency,
                description=f"Approved income payment: {obj.source}",
                income=obj,
                debit_account=cash_account,
                credit_account=revenue_account,
                created_by=request.user.get_full_name() or request.user.username
            )

    # ==========================
    # UPDATE REQUEST STATUS
    # ==========================
    edit_request.status = 'Approved'
    edit_request.approved_by = request.user
    edit_request.processed_at = timezone.now()
    edit_request.save()

    # ==========================
    # AUDIT LOG
    # ==========================
    audit_log(
        user=request.user,
        action='APPROVE',
        module='FINANCE',
        object_type='FinanceEditRequest',
        object_id=edit_request.id,
        description=f'Approved {edit_request.request_type} edit request',
        request=request
    )

    messages.success(request, "Request approved successfully.")

    return redirect('finance:pending_finance_edits')

@login_required
@transaction.atomic
def reject_finance_edit(request, pk):

    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('finance:dashboard')

    edit_request = get_object_or_404(FinanceEditRequest, pk=pk)

    if edit_request.status != 'Pending':
        messages.warning(request, "Request already processed.")
        return redirect('finance:pending_finance_edits')

    # Mark as Rejected
    edit_request.status = 'Rejected'
    edit_request.approved_by = request.user
    edit_request.processed_at = timezone.now()
    edit_request.save()

    # Audit log
    audit_log(
        user=request.user,
        action='REJECT',
        module='FINANCE',
        object_type='FinanceEditRequest',
        object_id=edit_request.id,
        description=f'Rejected {edit_request.request_type} edit request',
        request=request
    )

    messages.warning(request, "Request rejected.")

    return redirect('finance:pending_finance_edits')