# cornelsimba/finance/models.py - COMPLETE FIXED VERSION
from django.db import models
from hr.models import Employee
from procurement.models import PurchaseOrder
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.conf import settings  # Added import for settings
import logging
logger = logging.getLogger(__name__)


class Income(models.Model):
    INCOME_TYPES = [
        ('Sales', 'Sales Revenue'),
        ('Service', 'Service Income'),
        ('Interest', 'Interest Income'),
        ('Other', 'Other Income'),
    ]
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_by = models.CharField(max_length=100, blank=True, null=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Add these payment tracking fields
    is_paid = models.BooleanField(default=True)  # Default to True for existing records
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=[
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Card', 'Credit Card'),
        ('Mobile', 'Mobile Money'),
    ], default='Bank')
    
    source = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    # Currency field - Tsh is default
    currency = models.CharField(max_length=10, default='Tsh', choices=[
        ('Tsh', 'Tanzanian Shillings'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ])
    
    date = models.DateField()
    description = models.TextField(blank=True)
    income_type = models.CharField(max_length=20, choices=INCOME_TYPES, default='Sales')
    department = models.CharField(max_length=50, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Sales integration
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='income_records',
        help_text="Linked sale if income is from sales"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.source} - {self.amount_display} ({self.date})"
    
    @property
    def amount_display(self):
        """Display amount with proper currency symbol"""
        if self.currency == 'Tsh':
            return f"Tsh {self.amount:,.2f}"
        elif self.currency == 'USD':
            return f"${self.amount:,.2f}"
        elif self.currency == 'EUR':
            return f"€{self.amount:,.2f}"
        return f"{self.amount:,.2f}"
    
    def cancel(self, user, reason):
        """Mark income as cancelled instead of deleting"""
        self.is_active = False
        self.is_cancelled = True
        self.cancelled_by = user.get_full_name() or user.username
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()
        
        # Create reversal transaction
        try:
            from .models import Transaction, Account
            
            # Get accounts
            sales_account = Account.objects.filter(code='4000').first()
            cash_account = Account.objects.filter(code='1000').first()
            
            if sales_account and cash_account:
                Transaction.objects.create(
                    transaction_type='Adjustment',
                    amount=self.amount,
                    currency=self.currency,
                    description=f"Income cancelled: {self.source}. Reason: {reason}",
                    created_by=user.get_full_name() or user.username,
                    debit_account=sales_account,  # Revenue decreases (debit negative)
                    credit_account=cash_account,  # Cash decreases (credit negative)
                    income=self
                )
        except Exception as e:
            logger.warning(f"Reversal transaction failed: {e}")

        
        return self
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['income_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['sale']),
        ]

    @classmethod
    def create_from_sale(cls, sale, user=None):
        """Create income record from completed sale"""
        from sales.models import Sale
        
        if not isinstance(sale, Sale):
            raise ValueError("Must provide a Sale instance")
        
        if sale.status != 'COMPLETED':
            raise ValueError("Can only create income from completed sales")
        
        income = cls.objects.create(
            source=f"Sale: {sale.sale_number}",
            amount=sale.net_amount,
            currency=sale.currency or 'Tsh',
            date=sale.sale_date or timezone.now().date(),
            income_type='Sales',
            description=f"Sale to {sale.customer.name}. Items: {sale.item_count}",
            reference=sale.sale_number,
            sale=sale,
            is_paid=False,  # Sales income may not be paid immediately
            created_by=user.get_full_name() if user else 'System'
        )
        
        # Create transaction record
        try:
            from .models import Transaction, Account
            
            # Get or create sales income account
            sales_account, _ = Account.objects.get_or_create(
                code='4000',
                defaults={'name': 'Sales Revenue', 'account_type': 'Revenue'}
            )
            
            # Get or create cash/bank account
            cash_account, _ = Account.objects.get_or_create(
                code='1000',
                defaults={'name': 'Cash', 'account_type': 'Asset'}
            )
            
            Transaction.objects.create(
                transaction_type='Income',
                amount=sale.net_amount,
                description=f"Sale income: {sale.sale_number}",
                income=income,
                debit_account=cash_account,  # Cash increases (debit)
                credit_account=sales_account,  # Revenue increases (credit)
                created_by=user.get_full_name() if user else 'System'
            )
        except Exception as e:
            # If transaction fails, still keep the income record
            logger.warning(f"Transaction creation failed: {e}")

        
        return income


class Expense(models.Model):
    EXPENSE_TYPES = [
        ('Procurement', 'Purchase Order'),
        ('Salary', 'Employee Salary'),
        ('Utility', 'Utility Bills'),
        ('Office', 'Office Supplies'),
        ('Travel', 'Travel & Transport'),
        ('Marketing', 'Marketing'),
        ('Maintenance', 'Maintenance'),
        ('Other', 'Other Expense'),
    ]
    
    category = models.CharField(max_length=100)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES, default='Other')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    # Currency field
    currency = models.CharField(max_length=10, default='Tsh', choices=[
        ('Tsh', 'Tanzanian Shillings'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ])
    
    date = models.DateField()
    description = models.TextField(blank=True)
    
    # Integration with Procurement
    purchase_order = models.ForeignKey(
        'procurement.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    
    # Department tracking
    department = models.CharField(max_length=50, blank=True, null=True)
    
    # Payment tracking
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=[
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Card', 'Credit Card'),
    ], default='Bank')
    
    # Approval tracking
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} - {self.amount_display} ({self.date})"
    
    @property
    def amount_display(self):
        """Display amount with proper currency symbol"""
        if self.currency == 'Tsh':
            return f"Tsh {self.amount:,.2f}"
        elif self.currency == 'USD':
            return f"${self.amount:,.2f}"
        elif self.currency == 'EUR':
            return f"€{self.amount:,.2f}"
        return f"{self.amount:,.2f}"
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['expense_type']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['purchase_order']),
        ]


class Payroll(models.Model):
    MONTH_CHOICES = [
        ('January', 'January'), ('February', 'February'), ('March', 'March'),
        ('April', 'April'), ('May', 'May'), ('June', 'June'),
        ('July', 'July'), ('August', 'August'), ('September', 'September'),
        ('October', 'October'), ('November', 'November'), ('December', 'December')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payrolls')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pension_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    leave_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    year = models.IntegerField()

    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    currency = models.CharField(
        max_length=10,
        default='Tsh',
        choices=[
            ('Tsh', 'Tanzanian Shillings'),
            ('USD', 'US Dollars'),
            ('EUR', 'Euros'),
        ]
    )


    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_payrolls'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def gross_salary(self):
        return self.basic_salary + self.allowances

    def net_salary(self):
        total_deductions = (
            self.deductions +
            self.tax_amount +
            self.pension_amount +
            self.other_deductions +
            self.leave_deductions
        )
        return self.gross_salary() - total_deductions
        
    @property
    def net_salary_display(self):
        return f"Tsh {self.net_salary():,.2f}"


    def __str__(self):
        return f"{self.employee.full_name} - {self.month}/{self.year}"

    class Meta:
        unique_together = ['employee', 'month', 'year']
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['employee']),
            models.Index(fields=['month', 'year']),
            models.Index(fields=['is_paid']),
        ]


class Account(models.Model):
    """Simple accounting structure"""
    ACCOUNT_TYPES = [
        ('Asset', 'Asset'),
        ('Liability', 'Liability'),
        ('Equity', 'Equity'),
        ('Revenue', 'Revenue'),
        ('Expense', 'Expense'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        ordering = ['code']


class Transaction(models.Model):
    """Audit trail for all financial transactions"""
    TRANSACTION_TYPES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
        ('Payroll', 'Payroll'),
        ('Transfer', 'Transfer'),
        ('Adjustment', 'Adjustment'),
    ]
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Currency field
    currency = models.CharField(max_length=10, default='Tsh', choices=[
        ('Tsh', 'Tanzanian Shillings'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ])
    
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    
    # Links to specific records
    income = models.ForeignKey(Income, on_delete=models.SET_NULL, null=True, blank=True)
    expense = models.ForeignKey(Expense, on_delete=models.SET_NULL, null=True, blank=True)
    payroll = models.ForeignKey(Payroll, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Accounting entries
    debit_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='debit_transactions')
    credit_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='credit_transactions')
    
    # Created by
    created_by = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount_display} ({self.date.date()})"
    
    @property
    def amount_display(self):
        """Display amount with proper currency symbol"""
        if self.currency == 'Tsh':
            return f"Tsh {self.amount:,.2f}"
        elif self.currency == 'USD':
            return f"${self.amount:,.2f}"
        elif self.currency == 'EUR':
            return f"€{self.amount:,.2f}"
        return f"{self.amount:,.2f}"
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['date']),
            models.Index(fields=['debit_account']),
            models.Index(fields=['credit_account']),
        ]


class AccountingPeriod(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ('year', 'month')

    def __str__(self):
        return f"{self.month}/{self.year}"