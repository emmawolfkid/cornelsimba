from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Employee(models.Model):
    # Department choices - using your existing choices from forms.py
    DEPARTMENT_CHOICES = [
        ('', '--- Select Department ---'),
        ('HR', 'Human Resources'),
        ('Finance', 'Finance'),
        ('Procurement', 'Procurement'),
        ('Inventory', 'Inventory/Warehouse'),
        ('Auditor', 'Auditing'),
        ('IT', 'Information Technology'),
        ('Sales', 'Sales'),
        ('Administration', 'Administration'),
    ]
    
    # Position choices - limited options as requested
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
    
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    employee_id = models.CharField(max_length=20, unique=True, blank=True)  # Added blank=True
    full_name = models.CharField(max_length=100)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)  # Added choices
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)  # Added choices
    phone = models.CharField(max_length=20)
    address = models.TextField()
    date_joined = models.DateField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Auto-generate employee ID if not provided
        if not self.employee_id or self.employee_id.strip() == '':
            # Generate a unique ID like EMP-001, EMP-002, etc.
            last_employee = Employee.objects.order_by('id').last()
            if last_employee:
                try:
                    # Try to extract number from existing ID
                    last_id = int(last_employee.employee_id.split('-')[-1])
                    new_id = last_id + 1
                except (ValueError, IndexError):
                    new_id = 1
            else:
                new_id = 1
            
            self.employee_id = f"EMP-{new_id:03d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"
    
    def get_annual_leave_balance(self):
        """Calculate annual leave balance for this employee"""
        total_annual = LeaveType.objects.filter(name__icontains='annual').first()
        if not total_annual:
            return 0
        
        # Calculate used annual leave
        used_days = LeaveRequest.objects.filter(
            employee=self,
            leave_type__name__icontains='annual',
            status='approved'
        ).aggregate(total=models.Sum('days_requested'))['total'] or 0
        
        return total_annual.max_days - used_days
    
    def get_sick_leave_balance(self):
        """Calculate sick leave balance"""
        total_sick = LeaveType.objects.filter(name__icontains='sick').first()
        if not total_sick:
            return 0
        
        used_days = LeaveRequest.objects.filter(
            employee=self,
            leave_type__name__icontains='sick',
            status='approved'
        ).aggregate(total=models.Sum('days_requested'))['total'] or 0
        
        return total_sick.max_days - used_days
    
    class Meta:
        ordering = ['employee_id']

class LeaveType(models.Model):
    """Types of leave: Annual, Sick, Bereavement, Emergency, etc."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    max_days = models.IntegerField(default=0)  # 0 means unlimited
    is_paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    advance_notice_days = models.IntegerField(default=0)  # Days notice required
    
    def __str__(self):
        return f"{self.name} ({self.max_days} days)"

class LeaveRequest(models.Model):
    """Leave requests made by employees"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.IntegerField(default=1)
    reason = models.TextField()
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    rejected_date = models.DateTimeField(null=True, blank=True)
    
    # Approval chain
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    hr_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_approved_leaves')
    
    # For payroll integration
    is_paid_leave = models.BooleanField(default=True)
    payroll_processed = models.BooleanField(default=False)
    payroll_remarks = models.TextField(blank=True)
    
    # Supporting documents (optional)
    attachment = models.FileField(upload_to='leave_attachments/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Calculate days requested
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.days_requested = delta.days + 1  # Inclusive of both dates
        
        # Set is_paid_leave based on leave_type
        if self.leave_type:
            self.is_paid_leave = self.leave_type.is_paid
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    class Meta:
        ordering = ['-submitted_date']

@property
def is_paid_leave(self):
        """Check if this leave type is paid"""
        paid_leave_types = ['Annual Leave', 'Sick Leave', 'Maternity Leave']  # Add your paid types
        return self.leave_type.name in paid_leave_types if self.leave_type else True


class LeaveBalance(models.Model):
    """Track leave balances per employee per year"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField(default=timezone.now().year)
    total_days = models.IntegerField(default=0)
    used_days = models.IntegerField(default=0)
    remaining_days = models.IntegerField(default=0)
    carry_forward = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        self.remaining_days = self.total_days - self.used_days + self.carry_forward
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} {self.year}"
    
    class Meta:
        unique_together = ['employee', 'leave_type', 'year']