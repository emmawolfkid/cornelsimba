from django import forms
from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from hr.models import Employee
from inventory.models import Item
from django.core.exceptions import ValidationError
from django.utils import timezone

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'phone', 'email', 
            'address', 'tin_number', 'payment_terms', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255123456789'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'supplier@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'tin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TIN Number'}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Payment terms...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if Supplier.objects.filter(email=email).exists():
            if self.instance and self.instance.email == email:
                return email
            raise ValidationError('Supplier with this email already exists.')
        return email


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'requested_by', 'expected_delivery', 
            'department', 'cost_center', 'budget_code', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'requested_by': forms.Select(attrs={'class': 'form-control'}),
            'expected_delivery': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'cost_center': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cost Center'}),
            'budget_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Budget Code'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active suppliers
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
        # Only show active employees
        self.fields['requested_by'].queryset = Employee.objects.filter(is_active=True)
    
    def clean_expected_delivery(self):
        expected_delivery = self.cleaned_data['expected_delivery']
        if expected_delivery and expected_delivery < timezone.now().date():
            raise ValidationError('Expected delivery date cannot be in the past.')
        return expected_delivery


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'quantity', 'unit_price']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.all().order_by('name')


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)