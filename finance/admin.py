from django.contrib import admin
from .models import Income, Expense, Payroll, Account, Transaction
from django.utils.html import format_html

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('source', 'amount', 'income_type', 'date', 'department')
    list_filter = ('income_type', 'date', 'department')
    search_fields = ('source', 'description', 'reference')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('source', 'amount', 'date', 'income_type')
        }),
        ('Additional Information', {
            'fields': ('department', 'reference', 'description')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'expense_type', 'department', 'is_paid', 'date')
    list_filter = ('expense_type', 'is_paid', 'date', 'department', 'payment_method')
    search_fields = ('category', 'description', 'purchase_order__po_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'expense_type', 'amount', 'date')
        }),
        ('Source Information', {
            'fields': ('purchase_order', 'department')
        }),
        ('Payment Information', {
            'fields': ('is_paid', 'payment_date', 'payment_method', 'approved_by')
        }),
        ('Additional Information', {
            'fields': ('description', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('purchase_order', 'approved_by')


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'basic_salary', 'net_salary_display', 'is_paid')
    list_filter = ('month', 'year', 'is_paid', 'employee__department')
    search_fields = ('employee__full_name', 'employee__employee_id')
    readonly_fields = ('created_at', 'updated_at', 'net_salary_display', 'gross_salary_display', 'total_deductions_display')
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'month', 'year')
        }),
        ('Salary Details', {
            'fields': ('basic_salary', 'allowances', 'deductions')
        }),
        ('Statutory Deductions', {
            'fields': ('tax_amount', 'pension_amount', 'other_deductions')
        }),
        ('Payment Status', {
            'fields': ('is_paid', 'payment_date', 'approved_by')
        }),
        ('Calculations', {
            'fields': ('gross_salary_display', 'total_deductions_display', 'net_salary_display')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def net_salary_display(self, obj):
        return f"${obj.net_salary():.2f}"
    net_salary_display.short_description = 'Net Salary'
    
    def gross_salary_display(self, obj):
        return f"${obj.gross_salary():.2f}"
    gross_salary_display.short_description = 'Gross Salary'
    
    def total_deductions_display(self, obj):
        return f"${obj.total_deductions():.2f}"
    total_deductions_display.short_description = 'Total Deductions'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'balance', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name', 'description')
    list_editable = ('is_active', 'balance')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'date', 'debit_account', 'credit_account')
    list_filter = ('transaction_type', 'date')
    search_fields = ('description', 'debit_account__name', 'credit_account__name')
    readonly_fields = ('date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('debit_account', 'credit_account')