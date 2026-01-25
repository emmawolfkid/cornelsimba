from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from audit.models import AuditLog
from django.utils import timezone
from django.db.models import Count

# Import your HR models
try:
    from hr.models import Employee, LeaveRequest, LeaveType
except ImportError:
    # Fallback in case hr app is not available
    Employee = None
    LeaveRequest = None
    LeaveType = None

@login_required
def main_dashboard(request):
    user = request.user
    modules = set()
    
    # Add audit data for managers and admins
    audit_data = None
    if user.is_superuser or user.groups.filter(name__in=['Administrator', 'Manager', 'Auditor']).exists():
        # Get today's audit statistics
        today = timezone.now().date()
        today_logs = AuditLog.objects.filter(timestamp__date=today).count()
        
        # Get most active modules today
        module_activity = AuditLog.objects.filter(
            timestamp__date=today
        ).values('module').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Get recent audit logs
        recent_audit_logs = AuditLog.objects.all().order_by('-timestamp')[:5]
        
        audit_data = {
            'today_logs': today_logs,
            'module_activity': module_activity,
            'recent_audit_logs': recent_audit_logs,
        }

    # Determine access based on groups - FIXED GROUP NAMES (no spaces)
    if user.is_superuser or user.groups.filter(name='Administrator').exists():
        modules = ['HR', 'Finance', 'Inventory', 'Procurement', 'Sales', 'Audit']

    else:
     if user.groups.filter(name='HR').exists():
        modules.add('HR')

    if user.groups.filter(name='Finance').exists():
        modules.update(['Finance'])

    if user.groups.filter(name='Procurement').exists():
        modules.add('Procurement')

    if user.groups.filter(name='Inventory').exists():
        modules.add('Inventory')

    if user.groups.filter(name='Sales').exists():
        modules.add('Sales')

    if user.groups.filter(name='Auditor').exists():
        modules.add('Auditor')

    # --- LEAVE MANAGEMENT INTEGRATION ---
    user_has_employee = False
    annual_balance = 0
    sick_balance = 0
    user_is_manager = False
    pending_approvals = 0
    leave_notifications = []
    
    # Check if HR models are available
    if Employee and LeaveRequest:
        try:
            # Check if user has an employee record
            employee = Employee.objects.filter(user=user).first()
            if employee:
                user_has_employee = True
                
                # Get leave balances
                annual_balance = employee.get_annual_leave_balance() if hasattr(employee, 'get_annual_leave_balance') else 21
                sick_balance = employee.get_sick_leave_balance() if hasattr(employee, 'get_sick_leave_balance') else 14
                
                # Check if user is a manager
                user_is_manager = user.groups.filter(name='Manager').exists()
                
                # Get pending approvals for managers
                if user_is_manager:
                    pending_approvals = LeaveRequest.objects.filter(
                        employee__department=employee.department,
                        status='pending'
                    ).exclude(employee=employee).count()
                
                # Get recent leave status updates for this user (last 7 days)
                recent_status_changes = LeaveRequest.objects.filter(
                    employee=employee,
                    status__in=['approved', 'rejected'],
                    approved_date__gte=timezone.now() - timezone.timedelta(days=7)
                ).order_by('-approved_date')[:3]
                
                leave_notifications = [
                    {
                        'type': 'approved' if leave.status == 'approved' else 'rejected',
                        'message': f'Your {leave.leave_type.name} request for {leave.start_date.strftime("%b %d")} has been {leave.status}',
                        'date': leave.approved_date
                    }
                    for leave in recent_status_changes if leave.approved_date
                ]
                
        except Exception as e:
            # Log error but don't crash the dashboard
            print(f"Error loading leave data: {e}")
            user_has_employee = False
    
    # Default values for non-HR users
    else:
        # If HR app is not available, show default values
        user_has_employee = False
        annual_balance = 21
        sick_balance = 14
        user_is_manager = user.groups.filter(name='Manager').exists()

    return render(request, 'dashboard/main.html', {
        'modules': sorted(modules),
        'audit_data': audit_data,
        'user_groups': user.groups.count(),
        
        # Leave management data
        'user_has_employee': user_has_employee,
        'annual_balance': annual_balance,
        'sick_balance': sick_balance,
        'user_is_manager': user_is_manager,
        'pending_approvals': pending_approvals,
        'leave_notifications': leave_notifications,
    })