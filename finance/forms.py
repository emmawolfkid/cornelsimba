# cornelsimba/finance/forms.py - ENHANCED VERSION
from django import forms
from .models import Income, Expense, Payroll, Account
from hr.models import Employee
from procurement.models import PurchaseOrder
from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal


# cornelsimba/finance/forms.py - UPDATE IncomeForm
class IncomeForm(forms.ModelForm):
    # Source choices (removed income_type)
    SOURCE_CHOICES = [
        ('Sales Revenue', 'Sales Revenue'),
        ('Service Income', 'Service Income'),
        ('Interest Income', 'Interest Income'),
        ('Consulting Fees', 'Consulting Fees'),
        ('Rental Income', 'Rental Income'),
        ('Commission', 'Commission'),
        ('Other Income', 'Other Income'),
    ]
    
    # Department choices
    DEPARTMENT_CHOICES = [
        ('Sales', 'Sales'),
        ('Marketing', 'Marketing'),
        ('Finance', 'Finance'),
        ('Operations', 'Operations'),
        ('Services', 'Services'),
        ('Other', 'Other'),
    ]
    
    # Override fields
    source = forms.ChoiceField(
        choices=SOURCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Income
        fields = [
            'source', 'amount', 'currency', 'date',
            'department', 'reference', 'description'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description...'}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        return amount
    
    def clean_date(self):
        income_date = self.cleaned_data['date']
        if income_date > date.today():
            raise ValidationError('Income date cannot be in the future.')
        return income_date
    
    def clean_reference(self):
        reference = self.cleaned_data.get('reference', '').strip()
        
        # Auto-generate reference if not provided
        if not reference:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            reference = f"INC-{timestamp}"
        
        return reference
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default currency to Tsh
        if not self.instance.pk:
            self.initial.setdefault('currency', 'Tsh')
            self.initial.setdefault('date', date.today())


# cornelsimba/finance/forms.py - UPDATE ExpenseForm
class ExpenseForm(forms.ModelForm):
    # Department choices
    DEPARTMENT_CHOICES = [
        ('HR', 'Human Resources'),
        ('Sales', 'Sales'),
        ('Marketing', 'Marketing'),
        ('Finance', 'Finance'),
        ('Procurement', 'Procurement'),
        ('Inventory', 'Inventory'),
        ('IT', 'Information Technology'),
        ('Operations', 'Operations'),
        ('Maintenance', 'Maintenance'),
        ('Other', 'Other'),
    ]
    
    # Override department field
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Expense
        fields = [
            'expense_type', 'amount', 'date', 'department',
            'payment_method', 'currency', 'description'
        ]
        widgets = {
            'expense_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        
        # Check for manager approval threshold
        if amount > Decimal('5000000'):
            # This is handled in the view
            pass
        
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        
        # Auto-detect if manager approval is needed
        if amount and amount > Decimal('5000000'):
            # You can add logic here to auto-set a flag
            pass
        
        return cleaned_data
class PayrollForm(forms.ModelForm):
    # Add confirmation field for large amounts
    confirm_salary = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(),
        label='I confirm the salary amounts are correct'
    )
    
    class Meta:
        model = Payroll
        fields = [
            'employee', 'month', 'year', 'basic_salary',
            'allowances', 'deductions', 'tax_amount',
            'pension_amount', 'other_deductions', 'confirm_salary'
        ]
        widgets = {
            'employee': forms.Select(),
            'month': forms.Select(),
            'year': forms.NumberInput(attrs={'min': 2000, 'max': 2100}),
            'basic_salary': forms.TextInput(),
            'allowances': forms.TextInput(),
            'deductions': forms.TextInput(),
            'tax_amount': forms.TextInput(),
            'pension_amount': forms.TextInput(),
            'other_deductions': forms.TextInput(),
        }
    
    def clean_basic_salary(self):
        data = self.cleaned_data['basic_salary']
        # Remove commas if they exist and convert to Decimal
        if isinstance(data, str):
            data = data.replace(',', '')
        # Convert to Decimal
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            raise ValidationError('Please enter a valid number for basic salary.')
    
    # SIMPLIFY ALL OTHER clean methods - just convert to Decimal
    def clean_allowances(self):
        data = self.cleaned_data.get('allowances', '0')
        if isinstance(data, str):
            data = data.replace(',', '')
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def clean_deductions(self):
        data = self.cleaned_data.get('deductions', '0')
        if isinstance(data, str):
            data = data.replace(',', '')
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def clean_tax_amount(self):
        data = self.cleaned_data.get('tax_amount', '0')
        if isinstance(data, str):
            data = data.replace(',', '')
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def clean_pension_amount(self):
        data = self.cleaned_data.get('pension_amount', '0')
        if isinstance(data, str):
            data = data.replace(',', '')
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def clean_other_deductions(self):
        data = self.cleaned_data.get('other_deductions', '0')
        if isinstance(data, str):
            data = data.replace(',', '')
        try:
            return Decimal(str(data))
        except (ValueError, TypeError):
            return Decimal('0')
    
    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        basic_salary = cleaned_data.get('basic_salary', Decimal('0'))
        allowances = cleaned_data.get('allowances', Decimal('0'))
        
        # Check for duplicate payroll
        if employee and month and year:
            query = Payroll.objects.filter(employee=employee, month=month, year=year)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise ValidationError(f'Payroll already exists for {employee.full_name} - {month}/{year}')
        
        # Validate salary amounts
        gross_salary = basic_salary + allowances
        if gross_salary > Decimal('10000000'):  # 10 million Tsh
            raise ValidationError('Gross salary exceeds maximum limit. Requires HR Director approval.')
        
        # Validate deductions don't exceed salary
        # IMPORTANT: These are now DECIMALS from the clean methods
        total_deductions = (
            cleaned_data.get('deductions', Decimal('0')) +
            cleaned_data.get('tax_amount', Decimal('0')) +
            cleaned_data.get('pension_amount', Decimal('0')) +
            cleaned_data.get('other_deductions', Decimal('0'))
        )
        
        if total_deductions > gross_salary:
            raise ValidationError('Total deductions cannot exceed gross salary.')
        
        # Net salary validation
        net_salary = gross_salary - total_deductions
        if net_salary < Decimal('300000'):  # Minimum wage check (300k Tsh)
            raise ValidationError('Net salary is below minimum wage threshold.')
        
        return cleaned_data


class AccountForm(forms.ModelForm):
    """Form for managing chart of accounts"""
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1000, 4000'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account name'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data['code']
        
        # Validate account code format
        if not code.isdigit():
            raise ValidationError('Account code must contain only digits.')
        
        if len(code) != 4:
            raise ValidationError('Account code must be exactly 4 digits.')
        
        # Check for duplicates
        query = Account.objects.filter(code=code)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise ValidationError(f'Account code {code} already exists.')
        
        return code
    
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        
        # Check for duplicates (case-insensitive)
        query = Account.objects.filter(name__iexact=name)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise ValidationError(f'Account name "{name}" already exists.')
        
        return name


class IncomeCancellationForm(forms.Form):
    """Form for cancelling income records"""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide detailed reason for cancellation...'
        }),
        help_text="This reason will be recorded in the audit trail.",
        label="Cancellation Reason"
    )
    
    create_reversal = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Create reversal transaction in accounts",
        help_text="Uncheck if this is just an administrative correction"
    )
    
    def clean_reason(self):
        reason = self.cleaned_data['reason'].strip()
        if len(reason) < 10:
            raise ValidationError('Please provide a detailed reason (minimum 10 characters).')
        return reason


class ExpensePaymentForm(forms.ModelForm):
    """Form for marking expenses as paid"""
    class Meta:
        model = Expense
        fields = ['payment_date', 'payment_method']
        widgets = {
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault('payment_date', date.today())
    
    def clean_payment_date(self):
        payment_date = self.cleaned_data['payment_date']
        if payment_date > date.today():
            raise ValidationError('Payment date cannot be in the future.')
        return payment_date