# cornelsimba/finance/urls.py - COMPLETE VERSION
from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Dashboard
    path('', views.finance_dashboard, name='dashboard'),
    
    # Income
    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.income_create, name='income_create'),
    path('income/edit/<int:pk>/', views.income_edit, name='income_edit'),
    path('income/cancel/<int:pk>/', views.income_cancel, name='income_cancel'),
    path('income/<int:pk>/mark-paid/', views.income_mark_paid, name='income_mark_paid'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/edit/<int:pk>/', views.expense_edit, name='expense_edit'),  # ADDED
    path('expenses/<int:pk>/pay/', views.expense_mark_paid, name='expense_mark_paid'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    
    # Payroll
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/add/', views.payroll_create, name='payroll_create'),
    path('payroll/<int:pk>/pay/', views.payroll_mark_paid, name='payroll_mark_paid'),
    path('payroll/process-with-leaves/', views.process_payroll_with_leaves, name='process_payroll_with_leaves'),
    
    # Procurement Integration
    path('procurement/expenses/', views.procurement_expenses, name='procurement_expenses'),  # ADDED
    path('create-expense-from-po/<int:po_id>/', views.create_expense_from_po, name='create_expense_from_po'),
    
    # Reports
    path('reports/', views.financial_reports, name='reports'),
    
    # Accounting Tools
    path('cash-flow/', views.cash_flow_statement, name='cash_flow'),
    path('general-ledger/', views.general_ledger, name='general_ledger'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('income-statement/', views.income_statement, name='income_statement'),
    
    # PDF Download URLs - ADDED
  # PDF Download URLs - FIXED
path('financial-reports/pdf/', views.download_financial_report_pdf, name='download_financial_report_pdf'),
path('cash-flow/pdf/', views.download_cash_flow_pdf, name='download_cash_flow_pdf'),
path('trial-balance/pdf/', views.download_trial_balance_pdf, name='download_trial_balance_pdf'),
path('balance-sheet/pdf/', views.download_balance_sheet_pdf, name='download_balance_sheet_pdf'),
path('income-statement/pdf/', views.download_income_statement_pdf, name='download_income_statement_pdf'),
path('general-ledger/pdf/', views.download_general_ledger_pdf, name='download_general_ledger_pdf'),
]