# hr/context_processors.py
from django.utils import timezone

def leave_counts(request):
    """Add leave counts to all templates for navigation"""
    if not request.user.is_authenticated:
        return {}
    
    # Initialize with defaults
    pending_count = 0
    user_is_manager = request.user.groups.filter(name='Manager').exists()
    
    try:
        from .models import LeaveRequest, Employee
        
        # For managers: count leaves pending approval in their department
        if user_is_manager:
            try:
                manager_employee = request.user.employee
                if manager_employee:
                    pending_count = LeaveRequest.objects.filter(
                        employee__department=manager_employee.department,
                        status='pending'
                    ).exclude(employee=manager_employee).count()
            except Employee.DoesNotExist:
                pass
        
        # For HR: count all pending leaves
        elif request.user.groups.filter(name='HR').exists():
            pending_count = LeaveRequest.objects.filter(status='pending').count()
    
    except ImportError:
        # HR app not installed
        pass
    
    return {
        'pending_count': pending_count,
        'user_is_manager': user_is_manager,
    }