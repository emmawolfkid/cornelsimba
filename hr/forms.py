# hr/forms.py
from django import forms
from .models import Employee

# Define department choices
DEPARTMENT_CHOICES = [
    ('', '--- Select Department ---'),
    ('HR', 'Human Resources'),
    ('Finance', 'Finance'),
    ('Marketing', 'Marketing'),
    ('Procurement', 'Procurement'),
    ('Inventory', 'Inventory/Warehouse'),
    ('Safety', 'Safety & Compliance'),
    ('IT', 'Information Technology'),
    ('Operations', 'Operations'),
    ('Sales', 'Sales'),
    ('Administration', 'Administration'),
]

# Define position choices
POSITION_CHOICES = [
    ('', '--- Select Position ---'),
    ('Manager', 'Manager'),
    ('Supervisor', 'Supervisor'),
    ('Staff', 'Staff'),
    ('Officer', 'Officer'),
    ('Assistant', 'Assistant'),
    ('Director', 'Director'),
    ('Coordinator', 'Coordinator'),
]

class EmployeeForm(forms.ModelForm):
    # Override department field to use dropdown
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'required': 'required'})
    )
    
    # Add position field as dropdown
    position = forms.ChoiceField(
        choices=POSITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'required': 'required'})
    )
    
    class Meta:
        model = Employee
        fields = [
            'full_name', 
            'department', 
            'position',
            'phone',
            'address',
            'date_joined',
            'is_active'
        ]  # Removed employee_id from fields
        widgets = {
            'date_joined': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing employee, show the ID as read-only
        if self.instance and self.instance.employee_id:
            self.fields['employee_id_display'] = forms.CharField(
                initial=self.instance.employee_id,
                label='Employee ID',
                required=False,
                disabled=True,
                widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
            )