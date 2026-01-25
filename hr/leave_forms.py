# hr/leave_forms.py - COMPLETE FILE
from django import forms
from .models import LeaveRequest, LeaveType, Employee  # Added Employee
from django.utils import timezone



class LeaveRequestForm(forms.ModelForm):
    """Form for employees to request leave"""
    
    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Filter leave types based on employee or other criteria
        self.fields['leave_type'].queryset = LeaveType.objects.filter(requires_approval=True)
        
        # Set date input types
        self.fields['start_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['end_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        
        # Add Bootstrap classes
        for field in self.fields:
            if field not in ['attachment']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['reason'].widget.attrs.update({'rows': 4})
        self.fields['attachment'].required = False
    
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type',
            'start_date',
            'end_date',
            'reason',
            'emergency_contact',
            'emergency_phone',
            'attachment'
        ]
        widgets = {
            'reason': forms.Textarea(attrs={'placeholder': 'Please provide details for your leave request...'}),
        }

# hr/leave_forms.py - Make sure this form exists
class LeaveApprovalForm(forms.ModelForm):
    """Form for managers/HR to approve/reject leave"""
    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    manager_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional comment...'}),
        required=False
    )
    
    class Meta:
        model = LeaveRequest
        fields = []  # We only need the custom fields above
    
    def save(self, commit=True):
        # This form doesn't save the model, just returns cleaned data
        return self.cleaned_data

class HRLeaveForm(forms.ModelForm):
    """Form for HR to edit leave requests"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['attachment']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type',
            'start_date',
            'end_date',
            'status',
            'is_paid_leave',
            'payroll_processed',
            'payroll_remarks',
            'reason',
            'emergency_contact',
            'emergency_phone',
            'attachment'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'payroll_remarks': forms.Textarea(attrs={'rows': 2}),
        }


class HRAbsenceForm(forms.ModelForm):
    """Form for HR to add absence records for any employee"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set date input types
        self.fields['start_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['end_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['reason'].widget.attrs.update({'rows': 4, 'placeholder': 'Reason for absence...'})
        self.fields['payroll_remarks'].widget.attrs.update({'rows': 2})
        
        # Set employee queryset
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).order_by('full_name')
    
    class Meta:
        model = LeaveRequest
        fields = [
            'employee',
            'leave_type',
            'start_date',
            'end_date',
            'status',
            'is_paid_leave',
            'reason',
            'emergency_contact',
            'emergency_phone',
            'payroll_remarks',
            'attachment'
        ]
        widgets = {
            'payroll_remarks': forms.Textarea(attrs={'placeholder': 'Payroll processing notes...'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date.")
        
        return cleaned_data