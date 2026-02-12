# cornelsimba/sales/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Customer, Sale, SaleItem, Payment
from inventory.models import Item

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'customer_type', 'contact_person', 'phone', 
            'email', 'address', 'tax_id', 'credit_limit',
            'payment_terms', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'customer_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TIN/VAT Number'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Net 30'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'customer', 'sale_type', 'delivery_address',
            'delivery_date', 'discount_amount', 'notes', 'terms_conditions'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'sale_type': forms.Select(attrs={'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'terms_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True).order_by('name')


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['item', 'quantity', 'unit_price', 'tax_rate']
        
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control sale-item-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show items that are active and have stock
        self.fields['item'].queryset = Item.objects.filter(
            is_active=True, 
            quantity__gt=0
        ).order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity')
        
        if item and quantity:
            # Check stock availability
            if quantity > item.quantity:
                raise ValidationError({
                    'quantity': f'Insufficient stock! Available: {item.quantity} {item.unit_of_measure}'
                })
        
        return cleaned_data

# In cornelsimba/sales/forms.py
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'amount',
            'payment_method',
            'reference_number',  # REMOVE 'payment_status' from here
            'bank_name',
            'account_number',
            'cheque_number',
            'payment_date',
            'notes'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract sale from kwargs before calling parent
        self.sale = kwargs.pop('sale', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """Validate payment with sale context"""
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        
        if amount and self.sale:
            if amount > self.sale.balance_due:
                raise ValidationError(
                    f'Payment amount cannot exceed balance due (Tsh {self.sale.balance_due:,.2f})'
                )
        
        return cleaned_data


# Formset for multiple sale items
SaleItemFormSet = forms.inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    extra=0,              # 🔥 IMPORTANT CHANGE
    can_delete=True,
    min_num=1,
    validate_min=True
)
