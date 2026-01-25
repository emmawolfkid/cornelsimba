# cornelsimba/inventory/forms.py
from django import forms
from .models import Item, StockIn, StockOut, StockAdjustment
from django.core.exceptions import ValidationError
from django.utils import timezone

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            'name', 'sku', 'category', 'description', 
            'unit_of_measure', 'reorder_level', 'minimum_stock',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item Name'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU-001'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Item description...'}),
            'unit_of_measure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kg, pcs, liter'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.001'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.001'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'sku': 'Leave blank to auto-generate',
            'reorder_level': 'Alert when stock reaches this level',
            'minimum_stock': 'Critical level - take immediate action',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise ValidationError("Item name is required.")
        
        # Normalize: Proper capitalization for ALL words
        name = ' '.join(word.strip().title() for word in name.split())
        
        # Check for existing items (case-insensitive)
        query = Item.objects.filter(name__iexact=name, is_active=True)
        
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            existing_item = query.first()
            raise ValidationError(
                f"Item '{name}' already exists as '{existing_item.name}' (ID: {existing_item.id}). "
                f"Current stock: {existing_item.quantity} {existing_item.unit_of_measure}. "
                f"Please use the existing item or choose a different name."
            )
        
        return name
    
    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if not sku:
            from datetime import datetime
            sku = f"ITEM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return sku
    
    def clean(self):
        cleaned_data = super().clean()
        reorder_level = cleaned_data.get('reorder_level')
        minimum_stock = cleaned_data.get('minimum_stock')
        
        if reorder_level and minimum_stock:
            if minimum_stock >= reorder_level:
                raise ValidationError('Minimum stock should be less than reorder level.')
        
        return cleaned_data


class StockInForm(forms.ModelForm):
    class Meta:
        model = StockIn
        fields = [
            'item', 'quantity', 'source',
            'supplier', 'reference', 'notes'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.001, 'step': 0.001}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier name'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PO Number, GRN, etc.'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.filter(is_active=True).order_by('name')
        
        # Make sure we don't accidentally include category field
        if 'category' in self.fields:
            del self.fields['category']
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.created_by = self.user
        if commit:
            instance.save()
        return instance


class StockOutForm(forms.ModelForm):
    class Meta:
        model = StockOut
        fields = [
            'item', 'quantity', 'issued_to',
            'purpose', 'reference', 'notes'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.001, 'step': 0.001}),
            'issued_to': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Person or department (optional)'}),
            'purpose': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sales Order, Requisition, etc.'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.filter(is_active=True, quantity__gt=0).order_by('name')
        self.fields['quantity'].help_text = 'Enter quantity to issue'
        
        # Make sure we don't accidentally include category field
        if 'category' in self.fields:
            del self.fields['category']
    
    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity')
        
        if item and quantity:
            if quantity > item.quantity:
                raise ValidationError({
                    'quantity': f'Insufficient stock! Available: {item.quantity} {item.unit_of_measure}'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.created_by = self.user
        if commit:
            instance.save()
        return instance


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = [
            'item', 'adjustment_quantity', 'adjustment_type',
            'reason', 'reference_stock_in'
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'adjustment_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.001}),
            'adjustment_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Explain why this adjustment is needed...'}),
            'reference_stock_in': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'adjustment_quantity': 'Use negative numbers to reduce stock, positive to add',
            'reason': 'Be specific about the error or reason for adjustment',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.filter(is_active=True).order_by('name')
        self.fields['reference_stock_in'].queryset = StockIn.objects.filter(status='approved').order_by('-date')
    
    def clean_adjustment_quantity(self):
        quantity = self.cleaned_data.get('adjustment_quantity')
        if quantity == 0:
            raise ValidationError("Adjustment quantity cannot be zero.")
        return quantity
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.requested_by = self.user
        if commit:
            instance.save()
        return instance


class ApproveRejectForm(forms.Form):
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for rejection...'}),
        label='Rejection Reason'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if action == 'reject' and not rejection_reason:
            raise ValidationError({'rejection_reason': 'Please provide a reason for rejection'})
        
        return cleaned_data