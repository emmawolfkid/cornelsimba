from django import forms
from .models import Customer, Contract, Sale
from hr.models import Employee
from django.core.exceptions import ValidationError
from datetime import date


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'customer_type', 'contact_person', 'phone', 'email',
            'address', 'tin_number', 'credit_limit', 'payment_terms', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'customer_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255123456789'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'tin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TIN Number'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment terms...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_credit_limit(self):
        credit_limit = self.cleaned_data['credit_limit']
        if credit_limit < 0:
            raise ValidationError('Credit limit cannot be negative.')
        return credit_limit


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'customer', 'contract_type', 'description', 'start_date', 'end_date',
            'value', 'account_manager', 'payment_terms', 'renewal_date', 'notes'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Contract description...'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'account_manager': forms.Select(attrs={'class': 'form-control'}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment terms...'}),
            'renewal_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active customers
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True).order_by('name')
        # Only show active employees
        self.fields['account_manager'].queryset = Employee.objects.filter(is_active=True).order_by('full_name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError('End date must be after start date.')
            
            if start_date < date.today():
                raise ValidationError({'start_date': 'Start date cannot be in the past.'})
        
        return cleaned_data


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'contract', 'sale_type', 'quantity', 'unit_price',
            'sales_person', 'payment_status', 'invoice_number',
            'sale_date', 'due_date', 'item_description', 'notes'
        ]
        widgets = {
            'contract': forms.Select(attrs={'class': 'form-control'}),
            'sale_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'sales_person': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated if empty'}),
            'sale_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'item_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item/service sold'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active contracts
        self.fields['contract'].queryset = Contract.objects.filter(status='Active').order_by('-start_date')
        # Only show active employees
        self.fields['sales_person'].queryset = Employee.objects.filter(is_active=True).order_by('full_name')
    
    def clean(self):
        cleaned_data = super().clean()
        sale_date = cleaned_data.get('sale_date')
        due_date = cleaned_data.get('due_date')
        contract = cleaned_data.get('contract')
        
        if sale_date and contract:
            if sale_date < contract.start_date:
                raise ValidationError({'sale_date': f'Sale date cannot be before contract start date ({contract.start_date}).'})
            if sale_date > contract.end_date:
                raise ValidationError({'sale_date': f'Sale date cannot be after contract end date ({contract.end_date}).'})
        
        if sale_date and due_date:
            if sale_date > due_date:
                raise ValidationError({'due_date': 'Due date must be after sale date.'})
        
        return cleaned_data