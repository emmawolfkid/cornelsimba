# hr/admin.py
from django.contrib import admin
from .models import Employee, LeaveType, LeaveRequest, LeaveBalance

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_days', 'is_paid', 'requires_approval']
    list_filter = ['is_paid', 'requires_approval']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'submitted_date']
    list_filter = ['status', 'leave_type', 'employee__department']
    search_fields = ['employee__full_name', 'reason']
    date_hierarchy = 'submitted_date'

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'total_days', 'used_days', 'remaining_days']
    list_filter = ['year', 'leave_type']
    search_fields = ['employee__full_name']