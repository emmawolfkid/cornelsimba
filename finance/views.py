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
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.contrib.humanize.templatetags.humanize import intcomma

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
            form.save()
            
            # 🔴 AUDIT ADD - After this line
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
    """Edit an existing expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            
            # 🔴 AUDIT ADD - After this line
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
                f'Expense record updated: {expense.category} - {expense.amount_display}'
            )
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm(instance=expense)
    
    # IMPORTANT: Add expense_types to context
    context = {
        'form': form,
        'editing': True,
        'expense_types': Expense.EXPENSE_TYPES,  # Add this line
    }
    return render(request, 'finance/expense_form.html', context)


@login_required
@group_required('Finance')
def expense_mark_paid(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    
    if not expense.is_paid:
        expense.is_paid = True
        expense.payment_date = date.today()
        expense.save()
        
        # 🔴 AUDIT ADD - After this line
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
        
        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='UPDATE',
            module='FINANCE',
            object_type='Payroll',
            object_id=payroll.id,
            description=f'Marked payroll as paid for {payroll.employee.full_name} - {payroll.net_salary_display}',
            request=request
        )
        
        messages.success(request, 
            f'Payroll marked as paid for {payroll.employee.full_name} - {payroll.net_salary_display}'
        )
    
    return redirect('finance:payroll_list')


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
    """Financial reports dashboard - FIXED VERSION"""
    # Monthly summaries
    current_year = date.today().year
    
    # Monthly income
    monthly_income = []
    max_income = 0
    for month in range(1, 13):
        total = Income.objects.filter(
            date__year=current_year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_income.append({
            'month': date(2000, month, 1).strftime('%B'),
            'amount': total
        })
        max_income = max(max_income, total)
    
    # Monthly expense
    monthly_expense = []
    max_expense = 0
    for month in range(1, 13):
        total = Expense.objects.filter(
            date__year=current_year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_expense.append({
            'month': date(2000, month, 1).strftime('%B'),
            'amount': total
        })
        max_expense = max(max_expense, total)
    
    # Expense by category WITH PERCENTAGES
    total_expenses_all = Expense.objects.filter(
        date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    expense_by_category = []
    for category in Expense.objects.filter(date__year=current_year).values('expense_type').annotate(
        total=Sum('amount')
    ).order_by('-total'):
        percentage = (category['total'] / total_expenses_all * 100) if total_expenses_all > 0 else 0
        expense_by_category.append({
            'expense_type': category['expense_type'],
            'total': category['total'],
            'percentage': round(percentage, 1)
        })
    
    # Income by type WITH PERCENTAGES
    total_income_all = Income.objects.filter(
        date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    income_by_type = []
    for income_type in Income.objects.filter(date__year=current_year).values('income_type').annotate(
        total=Sum('amount')
    ).order_by('-total'):
        percentage = (income_type['total'] / total_income_all * 100) if total_income_all > 0 else 0
        income_by_type.append({
            'income_type': income_type['income_type'],
            'total': income_type['total'],
            'percentage': round(percentage, 1)
        })
    
    # Sales vs other income
    sales_income = Income.objects.filter(
        income_type='Sales',
        date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    other_income = Income.objects.filter(
        date__year=current_year
    ).exclude(income_type='Sales').aggregate(total=Sum('amount'))['total'] or 0
    
    total_income = sum(item['amount'] for item in monthly_income)
    total_expense = sum(item['amount'] for item in monthly_expense)
    profit_loss = total_income - total_expense
    
    # Calculate profit margin
    profit_margin = (profit_loss / total_income * 100) if total_income > 0 else 0
    
    context = {
        'current_year': current_year,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'expense_by_category': expense_by_category,
        'income_by_type': income_by_type,
        'sales_income': sales_income,
        'other_income': other_income,
        'total_income': total_income,
        'total_expense': total_expense,
        'profit_loss': profit_loss,
        'profit_margin': round(profit_margin, 1),
        'max_income': max_income,
        'max_expense': max_expense,
    }
    return render(request, 'finance/reports.html', context)

@login_required
@group_required('Finance')
def income_mark_paid(request, pk):
    """Mark income as paid"""
    income = get_object_or_404(Income, pk=pk)
    
    if not income.is_paid:
        income.is_paid = True
        income.payment_date = date.today()
        income.save()
        
        # 🔴 AUDIT ADD - After this line
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
    """Generate cash flow statement"""
    # Get date range (default to current month)
    end_date = date.today()
    start_date = end_date.replace(day=1)
    
    # Get parameters if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Calculate cash inflows (income paid in period)
    cash_inflows = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate cash outflows
    cash_outflows = Expense.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    payroll_outflows = Payroll.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum(F('basic_salary') + F('allowances')))['total'] or 0
    
    total_outflows = cash_outflows + payroll_outflows
    net_cash_flow = cash_inflows - total_outflows
    
    # Get total income for context
    total_income = Income.objects.filter(
        date__range=[start_date, end_date],
        is_active=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate available cash
    available_cash = cash_inflows - total_outflows
    
    # ========== ADD THESE CALCULATIONS ==========
    # Calculate cash conversion rate
    if total_income > 0:
        cash_conversion_rate = round((cash_inflows / total_income * 100), 1)
    else:
        cash_conversion_rate = 0
    
    # Calculate cash reserve coverage (months)
    if total_outflows > 0:
        cash_reserve_coverage = round((available_cash / total_outflows), 1)
    else:
        cash_reserve_coverage = 0
    # ========== END ADDITIONS ==========
    
    # Get transaction details
    income_transactions = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]
    
    expense_transactions = Expense.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]
    
    payroll_transactions = Payroll.objects.filter(
        is_paid=True,
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
        'available_cash': available_cash,
        'cash_conversion_rate': cash_conversion_rate,  # ADD THIS
        'cash_reserve_coverage': cash_reserve_coverage,  # ADD THIS
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
    """Profit & Loss Statement"""
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    filters = {}
    if start_date and end_date:
        filters['date__range'] = [
            datetime.strptime(start_date, '%Y-%m-%d').date(),
            datetime.strptime(end_date, '%Y-%m-%d').date()
        ]

    # Get accounts
    revenues = Account.objects.filter(account_type='Revenue')
    expenses = Account.objects.filter(account_type='Expense')

    total_revenue = 0
    total_expense = 0

    for acc in revenues:
        total_revenue += acc.credit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

    for acc in expenses:
        total_expense += acc.debit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0

    net_profit = total_revenue - total_expense

    return render(request, 'finance/income_statement.html', {
        'revenues': revenues,
        'expenses': expenses,
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
    """Download General Ledger as PDF - DIRECT VERSION"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    
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
    
    # Format currency
    def format_currency(value):
        return "{:,.2f}".format(value)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'transactions': transactions,
        'accounts_summary': accounts_summary,
        'debit_total': debit_total,
        'credit_total': credit_total,
        'debit_total_formatted': format_currency(debit_total),
        'credit_total_formatted': format_currency(credit_total),
        'balance_difference': balance_difference,
        'balance_difference_formatted': format_currency(balance_difference),
    }
    
    # Generate PDF directly
    try:
        template = get_template('finance/general_ledger_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"general_ledger_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        print(f"PDF Error: {e}")
    
    return HttpResponse("Error generating PDF", status=500)
@login_required
@group_required('Finance')
def download_trial_balance_pdf(request):
    """Download Trial Balance as PDF - FINAL FIXED VERSION"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    
    # Get accounts
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    total_debits = 0
    total_credits = 0
    
    # Prepare account data
    account_data = []
    for account in accounts:
        # Get transaction totals
        debit_total = account.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credit_total = account.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate balances
        if account.account_type in ['Asset', 'Expense']:
            debit_balance = debit_total - credit_total if debit_total > credit_total else 0
            credit_balance = credit_total - debit_total if credit_total > debit_total else 0
        else:
            credit_balance = credit_total - debit_total if credit_total > debit_total else 0
            debit_balance = debit_total - credit_total if debit_total > credit_total else 0
        
        account_dict = {
            'code': account.code,
            'name': account.name,
            'account_type': account.account_type,
            'debit_balance': debit_balance,
            'credit_balance': credit_balance,
            'is_debit': debit_balance > 0,
        }
        
        account_data.append(account_dict)
        total_debits += debit_balance
        total_credits += credit_balance
    
    # Check balance
    is_balanced = abs(total_debits - total_credits) < 0.01
    
    # Create context
    context = {
        'accounts': account_data,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'is_balanced': is_balanced,
        'abs_difference': abs(total_debits - total_credits),
        'date': date.today(),
    }
    
    # Generate PDF
    template = get_template('finance/trial_balance_pdf.html')
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('UTF-8')), dest=result)
    
    if pdf.err:
        # Return HTML as fallback
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="trial_balance.html"'
        return response
    
    # Return PDF
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    filename = f"trial_balance_{date.today().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
        

@login_required
@group_required('Finance')
def download_income_statement_pdf(request):
    """Download Income Statement as PDF - DIRECT VERSION"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    filters = {}
    if start_date and end_date:
        filters['date__range'] = [
            datetime.strptime(start_date, '%Y-%m-%d').date(),
            datetime.strptime(end_date, '%Y-%m-%d').date()
        ]

    # Get accounts
    revenues = Account.objects.filter(account_type='Revenue')
    expenses = Account.objects.filter(account_type='Expense')

    total_revenue = 0
    total_expense = 0
    
    revenue_details = []
    expense_details = []

    for acc in revenues:
        revenue_amount = acc.credit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_revenue += revenue_amount
        if revenue_amount > 0:
            revenue_details.append({
                'account': acc,
                'amount': revenue_amount
            })

    for acc in expenses:
        expense_amount = acc.debit_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_expense += expense_amount
        if expense_amount > 0:
            expense_details.append({
                'account': acc,
                'amount': expense_amount
            })

    net_profit = total_revenue - total_expense
    
    # Format currency
    def format_currency(value):
        return "{:,.2f}".format(value)

    context = {
        'revenue_details': revenue_details,
        'expense_details': expense_details,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'total_revenue_formatted': format_currency(total_revenue),
        'total_expense_formatted': format_currency(total_expense),
        'net_profit_formatted': format_currency(net_profit),
        'start_date': start_date,
        'end_date': end_date,
        'date': date.today(),
    }
    
    # Generate PDF directly
    try:
        template = get_template('finance/income_statement_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"income_statement_{start_date or ''}_to_{end_date or date.today()}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        print(f"PDF Error: {e}")
    
    return HttpResponse("Error generating PDF", status=500)
@login_required
@group_required('Finance')
def download_cash_flow_pdf(request):
    """Download Cash Flow Statement as PDF - DIRECT VERSION"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    
    # Get date range (default to current month)
    end_date = date.today()
    start_date = end_date.replace(day=1)
    
    # Get parameters if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Calculate cash inflows (income paid in period)
    cash_inflows = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate cash outflows
    cash_outflows = Expense.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    payroll_outflows = Payroll.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum(F('basic_salary') + F('allowances')))['total'] or 0
    
    total_outflows = cash_outflows + payroll_outflows
    net_cash_flow = cash_inflows - total_outflows
    
    # Get transaction details
    income_transactions = Income.objects.filter(
        is_paid=True,
        is_active=True,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]
    
    expense_transactions = Expense.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]
    
    payroll_transactions = Payroll.objects.filter(
        is_paid=True,
        payment_date__range=[start_date, end_date]
    ).order_by('-payment_date')[:20]
    
    # Format currency
    def format_currency(value):
        return "{:,.2f}".format(value)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'cash_inflows': cash_inflows,
        'cash_outflows': cash_outflows,
        'payroll_outflows': payroll_outflows,
        'total_outflows': total_outflows,
        'net_cash_flow': net_cash_flow,
        'cash_inflows_formatted': format_currency(cash_inflows),
        'cash_outflows_formatted': format_currency(cash_outflows),
        'payroll_outflows_formatted': format_currency(payroll_outflows),
        'total_outflows_formatted': format_currency(total_outflows),
        'net_cash_flow_formatted': format_currency(net_cash_flow),
        'income_transactions': income_transactions,
        'expense_transactions': expense_transactions,
        'payroll_transactions': payroll_transactions,
    }
    
    # Generate PDF directly
    try:
        template = get_template('finance/cash_flow_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"cash_flow_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        print(f"PDF Error: {e}")
    
    return HttpResponse("Error generating PDF", status=500)
@login_required
@group_required('Finance')
def download_financial_report_pdf(request):
    """Download Financial Report as PDF - DIRECT VERSION"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    
    current_year = date.today().year
    
    # Get all the same data as the regular report view
    monthly_income = []
    for month in range(1, 13):
        total = Income.objects.filter(
            date__year=current_year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_income.append({
            'month': date(2000, month, 1).strftime('%B'),
            'amount': total
        })
    
    monthly_expense = []
    for month in range(1, 13):
        total = Expense.objects.filter(
            date__year=current_year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_expense.append({
            'month': date(2000, month, 1).strftime('%B'),
            'amount': total
        })
    
    # Calculate totals
    total_income = sum(item['amount'] for item in monthly_income)
    total_expense = sum(item['amount'] for item in monthly_expense)
    profit_loss = total_income - total_expense
    
    # Format currency
    def format_currency(value):
        return "{:,.2f}".format(value)
    
    context = {
        'current_year': current_year,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'total_income': total_income,
        'total_expense': total_expense,
        'profit_loss': profit_loss,
        'total_income_formatted': format_currency(total_income),
        'total_expense_formatted': format_currency(total_expense),
        'profit_loss_formatted': format_currency(profit_loss),
        'date': date.today(),
    }
    
    # Generate PDF directly
    try:
        template = get_template('finance/financial_report_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"financial_report_{current_year}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        print(f"PDF Error: {e}")
    
    return HttpResponse("Error generating PDF", status=500)
@login_required
@group_required('Finance')
def download_balance_sheet_pdf(request):
    """Download Balance Sheet as PDF with REAL data"""
    from django.http import HttpResponse
    from django.template.loader import get_template
    from io import BytesIO
    from xhtml2pdf import pisa
    from django.db.models import Sum
    
    # Get ALL accounts with their balances
    assets = Account.objects.filter(account_type='Asset')
    liabilities = Account.objects.filter(account_type='Liability')
    equity = Account.objects.filter(account_type='Equity')
    
    # Prepare detailed lists for each category
    asset_details = []
    liability_details = []
    equity_details = []
    
    total_assets = 0
    total_liabilities = 0
    total_equity = 0
    
    # Calculate asset balances
    for acc in assets:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        balance = debits - credits
        
        if balance != 0:
            asset_details.append({
                'name': acc.name,
                'balance': balance
            })
            total_assets += balance
    
    # Calculate liability balances
    for acc in liabilities:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        balance = credits - debits  # Liabilities are credit normal
        
        if balance != 0:
            liability_details.append({
                'name': acc.name,
                'balance': balance
            })
            total_liabilities += balance
    
    # Calculate equity balances
    for acc in equity:
        debits = acc.debit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        credits = acc.credit_transactions.aggregate(total=Sum('amount'))['total'] or 0
        balance = credits - debits  # Equity is credit normal
        
        if balance != 0:
            equity_details.append({
                'name': acc.name,
                'balance': balance
            })
            total_equity += balance
    
    # Format numbers with commas
    def format_currency(value):
        return "{:,.2f}".format(value)
    
    # Calculate if balanced
    is_balanced = abs(total_assets - (total_liabilities + total_equity)) < 1
    difference = total_assets - (total_liabilities + total_equity)
    
    context = {
        # Detailed account lists
        'asset_details': asset_details,
        'liability_details': liability_details,
        'equity_details': equity_details,
        
        # Totals
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        
        # Formatted totals
        'total_assets_formatted': format_currency(total_assets),
        'total_liabilities_formatted': format_currency(total_liabilities),
        'total_equity_formatted': format_currency(total_equity),
        'liabilities_plus_equity_formatted': format_currency(total_liabilities + total_equity),
        'difference_formatted': format_currency(abs(difference)),
        
        # Status
        'is_balanced': is_balanced,
        'date': date.today(),
    }
    
    # Generate PDF
    try:
        template = get_template('finance/balance_sheet_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"balance_sheet_{date.today()}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        print(f"PDF Error: {e}")
    
    return HttpResponse("Error generating PDF", status=500)