# hr/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Employee
from .forms import EmployeeForm
from django.contrib.auth.models import User
from functools import wraps
from audit.utils import audit_log
from .models import LeaveRequest, LeaveType, LeaveBalance
from .leave_forms import LeaveRequestForm, LeaveApprovalForm, HRLeaveForm, HRAbsenceForm
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from django.http import HttpResponse

# Helper function to restrict access by group - SINGLE VERSION
def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                return redirect('/')
        return _wrapped_view
    return decorator

# Helper function to sanitize text for audit logs
def sanitize_audit_text(text):
    """Replace problematic Unicode characters in audit log text"""
    replacements = {
        '→': '->',
        '←': '<-',
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    return text

# hr/views.py - Update hr_dashboard function
@login_required
@group_required('HR')
def hr_dashboard(request):
    employees = Employee.objects.all()[:5]
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    
    # Get user's employee record
    user_has_employee = False
    user_employee = None
    is_manager = request.user.groups.filter(name='Manager').exists()
    is_hr = request.user.groups.filter(name='HR').exists()
    
    try:
        user_employee = request.user.employee
        user_has_employee = True
    except:
        pass
    
    # Get leave data
    total_pending_leaves = LeaveRequest.objects.filter(status='pending').count()
    today_leaves = LeaveRequest.objects.filter(
        submitted_date__date=timezone.now().date()
    ).count()
    
    # Calculate active absences (approved leaves that are happening today)
    today = timezone.now().date()
    active_absences = LeaveRequest.objects.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).count()
    
    # Get pending leaves for manager
    pending_leaves = None
    pending_approvals_count = 0
    if is_manager and user_employee:
        pending_leaves = LeaveRequest.objects.filter(
            employee__department=user_employee.department,
            status='pending'
        ).exclude(employee=user_employee)[:5]
        pending_approvals_count = LeaveRequest.objects.filter(
            employee__department=user_employee.department,
            status='pending'
        ).exclude(employee=user_employee).count()
    
    context = {
        'employees': employees,
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_pending_leaves': total_pending_leaves,
        'today_leaves': today_leaves,
        'active_absences': active_absences,
        'is_manager': is_manager,
        'is_hr': is_hr,
        'user_has_employee': user_has_employee,
        'user_employee': user_employee,
        'pending_leaves': pending_leaves,
        'pending_approvals_count': pending_approvals_count,
    }
    return render(request, 'hr/dashboard.html', context)

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

@login_required
@group_required('HR')
def employee_list(request):
    # Get all employees
    employees_list = Employee.objects.all().select_related('user').order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    # Apply filters
    if search_query:
        employees_list = employees_list.filter(
            Q(full_name__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            employees_list = employees_list.filter(is_active=True)
        elif status_filter == 'inactive':
            employees_list = employees_list.filter(is_active=False)
    
    if department_filter:
        employees_list = employees_list.filter(department=department_filter)
    
    # Get unique departments for filter dropdown
    departments = Employee.objects.values_list('department', flat=True).distinct().exclude(department__isnull=True).exclude(department='').order_by('department')
    
    # Count statistics
    total_count = employees_list.count()
    active_count = employees_list.filter(is_active=True).count()
    inactive_count = employees_list.filter(is_active=False).count()
    
    # Calculate department distribution
    department_distribution = {}
    for dept in departments:
        count = Employee.objects.filter(department=dept).count()
        department_distribution[dept] = count
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(employees_list, 20)  # Show 20 employees per page
    
    try:
        employees = paginator.page(page)
    except PageNotAnInteger:
        employees = paginator.page(1)
    except EmptyPage:
        employees = paginator.page(paginator.num_pages)
    
    # Calculate active percentage
    active_percentage = int((active_count / total_count * 100)) if total_count > 0 else 0
    
    context = {
        'employees': employees,
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'departments': departments,
        'departments_count': departments.count(),
        'department_distribution': department_distribution,
        'active_percentage': active_percentage,
        'search_query': search_query,
        'status_filter': status_filter,
        'department_filter': department_filter,
    }
    return render(request, 'hr/employee_list.html', context)

@login_required
@group_required('HR')
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    context = {'employee': employee}
    return render(request, 'hr/employee_detail.html', context)

@login_required
@group_required('HR')
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            
            # AUDIT LOG
            audit_log(
                user=request.user,
                action='CREATE',
                module='HR',
                object_type='Employee',
                object_id=employee.id,
                description=sanitize_audit_text(f'Created employee record for: {employee.full_name}'),
                request=request
            )
            
            return redirect('hr:employee_list')
    else:
        form = EmployeeForm()
    
    context = {'form': form, 'title': 'Add New Employee'}
    return render(request, 'hr/employee_form.html', context)

@login_required
@group_required('HR')
def employee_update(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            old_name = employee.full_name  # Save old name
            form.save()
            
            # AUDIT LOG - FIXED: Removed arrow character
            audit_log(
                user=request.user,
                action='UPDATE',
                module='HR',
                object_type='Employee',
                object_id=employee.id,
                description=sanitize_audit_text(f'Updated employee record: {old_name} to {employee.full_name}'),
                request=request
            )
            
            return redirect('hr:employee_detail', employee_id=employee.id)
    else:
        form = EmployeeForm(instance=employee)
    
    context = {'form': form, 'title': 'Edit Employee', 'employee': employee}
    return render(request, 'hr/employee_form.html', context)

@login_required
@group_required('HR')
def employee_delete(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        employee_name = employee.full_name  # Save before deleting
        
        employee.delete()
        
        # AUDIT LOG
        audit_log(
            user=request.user,
            action='DELETE',
            module='HR',
            object_type='Employee',
            object_id=employee_id,
            description=sanitize_audit_text(f'Deleted employee: {employee_name}'),
            request=request
        )
        
        return redirect('hr:employee_list')
    
    context = {'employee': employee}
    return render(request, 'hr/employee_confirm_delete.html', context)

@login_required
@group_required('HR')
def user_sync_view(request):
    """Show users that don't have employee records yet"""
    # Get all users
    all_users = User.objects.all()
    
    # Get users who already have employee records
    users_with_employees = User.objects.filter(employee__isnull=False)
    
    # Get users without employee records (need HR to create)
    users_without_employees = User.objects.filter(employee__isnull=True)
    
    context = {
        'all_users': all_users,
        'users_with_employees': users_with_employees,
        'users_without_employees': users_without_employees,
    }
    return render(request, 'hr/user_sync.html', context)

@login_required
@group_required('HR')
def create_employee_from_user(request, user_id):
    """Create employee record from existing user"""
    user = get_object_or_404(User, id=user_id)
    
    # Check if employee already exists for this user
    if hasattr(user, 'employee'):
        messages.error(request, f"Employee record already exists for {user.username}")
        return redirect('hr:user_sync')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            # Double check (in case of race condition)
            if hasattr(user, 'employee'):
                messages.error(request, f"Employee record already exists for {user.username}")
                return redirect('hr:user_sync')
            
            employee = form.save(commit=False)
            employee.user = user  # Link to the user
            employee.save()
            
            # AUDIT LOG
            audit_log(
                user=request.user,
                action='CREATE',
                module='HR',
                object_type='Employee',
                object_id=employee.id,
                description=sanitize_audit_text(f'Created employee record for user: {user.username} for {employee.full_name}'),
                request=request
            )
            
            messages.success(request, f"Employee record created successfully for {user.username}")
            return redirect('hr:employee_detail', employee_id=employee.id)
    else:
        # Pre-fill form with user data
        initial_data = {
            'full_name': user.get_full_name() or user.username,
        }
        form = EmployeeForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': f'Create Employee Record for {user.username}',
        'user': user,
    }
    return render(request, 'hr/employee_form.html', context)

# ===== LEAVE MANAGEMENT VIEWS =====

@login_required
def leave_dashboard(request):
    """Dashboard showing leave statistics and requests"""
    # Check if user has employee record
    try:
        employee = request.user.employee
        my_leaves = LeaveRequest.objects.filter(employee=employee).order_by('-submitted_date')[:5]
    except:
        employee = None
        my_leaves = None
    
    # Determine user role
    is_hr = request.user.groups.filter(name='HR').exists()
    is_manager = request.user.groups.filter(name='Manager').exists()
    is_finance = request.user.groups.filter(name='Finance').exists()
    
    # Get pending leaves for approval (for managers/HR)
    pending_for_approval = None
    if is_manager or is_hr:
        # Managers see their department's pending leaves
        if is_manager and employee:
            pending_for_approval = LeaveRequest.objects.filter(
                employee__department=employee.department,
                status='pending'
            ).exclude(employee=employee)
        # HR sees all pending leaves
        elif is_hr:
            pending_for_approval = LeaveRequest.objects.filter(status='pending')
    
    # Get recent approved leaves (for Finance)
    recent_approved = None
    if is_finance:
        recent_approved = LeaveRequest.objects.filter(
            status='approved',
            payroll_processed=False
        ).order_by('-approved_date')[:10]
    
    context = {
        'employee': employee,
        'my_leaves': my_leaves,
        'pending_for_approval': pending_for_approval,
        'recent_approved': recent_approved,
        'is_hr': is_hr,
        'is_manager': is_manager,
        'is_finance': is_finance,
    }
    return render(request, 'hr/leave_dashboard.html', context)

@login_required
def leave_request_create(request):
    """Employee creates a new leave request"""
    try:
        employee = request.user.employee
    except:
        messages.error(request, 'You need an employee record to request leave.')
        return redirect('hr:leave_dashboard')
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES, employee=employee)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            
            # Check leave balance
            leave_balance = employee.get_annual_leave_balance() if 'annual' in leave_request.leave_type.name.lower() else 0
            if leave_balance < leave_request.days_requested:
                messages.warning(request, f'Warning: You only have {leave_balance} days remaining for this leave type.')
            
            leave_request.save()
            
            # Audit log
            audit_log(
                user=request.user,
                action='CREATE',
                module='HR-Leave',
                object_type='LeaveRequest',
                object_id=leave_request.id,
                description=sanitize_audit_text(f'Submitted leave request: {leave_request.leave_type.name} for {leave_request.days_requested} days'),
                request=request
            )
            
            messages.success(request, 'Leave request submitted successfully!')
            return redirect('hr:leave_dashboard')
    else:
        form = LeaveRequestForm(employee=employee)
    
    context = {
        'form': form,
        'title': 'Request Leave',
        'employee': employee,
    }
    return render(request, 'hr/leave_form.html', context)

@login_required
def my_leave_requests(request):
    """View all leave requests for current employee"""
    try:
        employee = request.user.employee
    except:
        messages.error(request, 'You need an employee record to view leave requests.')
        return redirect('hr:leave_dashboard')
    
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-submitted_date')
    
    context = {
        'leaves': leaves,
        'employee': employee,
    }
    return render(request, 'hr/my_leave_requests.html', context)

@login_required
def leave_request_detail(request, leave_id):
    """View details of a specific leave request"""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    # Permission check
    try:
        employee = request.user.employee
    except:
        employee = None
    
    is_hr = request.user.groups.filter(name='HR').exists()
    is_manager = request.user.groups.filter(name='Manager').exists()
    can_view = False
    
    if is_hr:
        can_view = True
    elif is_manager and employee and leave.employee.department == employee.department:
        can_view = True
    elif employee and leave.employee == employee:
        can_view = True
    
    if not can_view:
        messages.error(request, 'You do not have permission to view this leave request.')
        return render(request, 'hr/no_access.html', status=403)
    
    context = {
        'leave': leave,
        'employee': employee,
        'is_hr': is_hr,
        'is_manager': is_manager,
    }
    return render(request, 'hr/leave_detail.html', context)

# ===== MANAGER/HR APPROVAL VIEWS =====
@login_required
def leave_approval_list(request):
    """List of leaves pending approval - accessible to both Managers and HR"""
    try:
        user_employee = request.user.employee
    except:
        user_employee = None
    
    # HR sees all pending leaves, Managers see only their department
    is_hr = request.user.groups.filter(name='HR').exists()
    is_manager = request.user.groups.filter(name='Manager').exists()
    
    if not (is_hr or is_manager):
        messages.error(request, 'You do not have permission to access leave approvals.')
        return redirect('hr:leave_dashboard')
    
    if is_hr:
        # HR can see all pending leaves
        pending_leaves = LeaveRequest.objects.filter(status='pending').order_by('-submitted_date')
    elif is_manager and user_employee:
        # Managers see their department's pending leaves
        pending_leaves = LeaveRequest.objects.filter(
            employee__department=user_employee.department,
            status='pending'
        ).exclude(employee=user_employee).order_by('-submitted_date')
    else:
        pending_leaves = []
        if is_manager:
            messages.warning(request, 'You need an employee record to approve leaves.')
    
    context = {
        'pending_leaves': pending_leaves,
        'user_employee': user_employee,
        'is_hr': is_hr,
        'is_manager': is_manager,
    }
    return render(request, 'hr/leave_approval_list.html', context)

@login_required
def leave_approve_reject(request, leave_id):
    """Manager/HR approves or rejects a leave request"""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    # Check permissions - User must be either HR or Manager
    is_hr = request.user.groups.filter(name='HR').exists()
    is_manager = request.user.groups.filter(name='Manager').exists()
    
    if not (is_hr or is_manager):
        messages.error(request, 'You do not have permission to approve leaves.')
        return redirect('hr:leave_dashboard')
    
    # Additional manager-specific check
    if is_manager and not is_hr:
        try:
            user_employee = request.user.employee
        except:
            messages.error(request, 'You need an employee record to approve leaves.')
            return redirect('hr:leave_approval_list')
        
        if not user_employee:
            messages.error(request, 'You need an employee record to approve leaves.')
            return redirect('hr:leave_approval_list')
        
        if leave.employee.department != user_employee.department:
            messages.error(request, 'You can only approve leaves for your own department.')
            return redirect('hr:leave_approval_list')
    
    # Check if leave is already processed
    if leave.status != 'pending':
        messages.warning(request, f'This leave request is already {leave.status}.')
        return redirect('hr:leave_detail', leave_id=leave.id)
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            comment = form.cleaned_data['manager_comment']
            
            # Update the leave object
            if action == 'approve':
                leave.status = 'approved'
                leave.approved_by = request.user
                leave.approved_date = timezone.now()
                success_message = f'Leave request for {leave.employee.full_name} has been approved.'
            else:
                leave.status = 'rejected'
                leave.rejected_date = timezone.now()
                success_message = f'Leave request for {leave.employee.full_name} has been rejected.'
            
            # Add comment if provided
            if comment:
                leave.reason += f"\n\n--- {request.user.get_full_name() or request.user.username} ({timezone.now().strftime('%Y-%m-%d %H:%M')}) ---\n{comment}"
            
            leave.save()
            
            # Audit log
            audit_log(
                user=request.user,
                action='APPROVE' if action == 'approve' else 'REJECT',
                module='HR-Leave',
                object_type='LeaveRequest',
                object_id=leave.id,
                description=sanitize_audit_text(f'{action.capitalize()}d leave request for {leave.employee.full_name}'),
                old_values={'status': 'pending'},
                new_values={'status': leave.status, 'action_by': request.user.username},
                request=request
            )
            
            messages.success(request, success_message)
            return redirect('hr:leave_approval_list')
        else:
            # Form is invalid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LeaveApprovalForm()
    
    context = {
        'form': form,
        'leave': leave,
        'title': 'Approve/Reject Leave Request',
        'is_hr': is_hr,
        'is_manager': is_manager,
    }
    return render(request, 'hr/leave_approval_form.html', context)

# ===== HR MANAGEMENT VIEWS =====

@login_required
@group_required('HR')
def hr_leave_management(request):
    """HR view for managing all leaves"""
    leaves = LeaveRequest.objects.all().order_by('-submitted_date')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    # Apply filters
    filtered_leaves = leaves
    if status_filter:
        filtered_leaves = filtered_leaves.filter(status=status_filter)
    if department_filter:
        filtered_leaves = filtered_leaves.filter(employee__department=department_filter)
    
    # Calculate counts for ALL leaves (not filtered)
    all_leaves_count = leaves.count()
    approved_count = leaves.filter(status='approved').count()
    pending_count = leaves.filter(status='pending').count()
    rejected_count = leaves.filter(status='rejected').count()
    cancelled_count = leaves.filter(status='cancelled').count()
    
    # Calculate counts for filtered leaves (for filter badges)
    filtered_approved_count = filtered_leaves.filter(status='approved').count()
    filtered_pending_count = filtered_leaves.filter(status='pending').count()
    filtered_rejected_count = filtered_leaves.filter(status='rejected').count()
    filtered_cancelled_count = filtered_leaves.filter(status='cancelled').count()
    
    # Get unique departments for filter dropdown
    departments = Employee.objects.values_list('department', flat=True).distinct().exclude(department__isnull=True).exclude(department='').order_by('department')
    
    context = {
        'leaves': filtered_leaves,  # Use filtered leaves for the table
        'all_leaves_count': all_leaves_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'cancelled_count': cancelled_count,
        'filtered_approved_count': filtered_approved_count,
        'filtered_pending_count': filtered_pending_count,
        'filtered_rejected_count': filtered_rejected_count,
        'filtered_cancelled_count': filtered_cancelled_count,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'departments': departments,  # Add departments to context
    }
    return render(request, 'hr/hr_leave_management.html', context)

@login_required
@group_required('HR')
def hr_leave_edit(request, leave_id):
    """HR can edit any leave request"""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    if request.method == 'POST':
        old_status = leave.status
        
        form = HRLeaveForm(request.POST, request.FILES, instance=leave)
        if form.is_valid():
            form.save()
            
            # Audit log
            audit_log(
                user=request.user,
                action='UPDATE',
                module='HR-Leave',
                object_type='LeaveRequest',
                object_id=leave.id,
                description=sanitize_audit_text(f'HR updated leave request for {leave.employee.full_name}'),
                old_values={'status': old_status},
                new_values={'status': leave.status},
                request=request
            )
            
            messages.success(request, 'Leave request updated successfully!')
            return redirect('hr:hr_leave_management')
    else:
        form = HRLeaveForm(instance=leave)
    
    context = {
        'form': form,
        'leave': leave,
        'title': 'Edit Leave Request',
    }
    return render(request, 'hr/leave_form.html', context)

@login_required
@group_required('HR')
def hr_leave_add(request):
    """HR can add leave/absence records for any employee"""
    if request.method == 'POST':
        form = HRAbsenceForm(request.POST)
        if form.is_valid():
            leave = form.save()
            
            # Audit log
            audit_log(
                user=request.user,
                action='CREATE',
                module='HR-Leave',
                object_type='LeaveRequest',
                object_id=leave.id,
                description=sanitize_audit_text(f'HR added absence record for {leave.employee.full_name}: {leave.leave_type.name}'),
                request=request
            )
            
            messages.success(request, f'Absence record added for {leave.employee.full_name}')
            return redirect('hr:hr_leave_management')
    else:
        form = HRAbsenceForm()
    
    context = {
        'form': form,
        'title': 'Add Absence Record',
    }
    return render(request, 'hr/hr_leave_add.html', context)

# ===== FINANCE VIEWS =====

@login_required
def finance_leaves_view(request):
    """Finance view for leaves that need payroll processing"""
    # Check if user is in Finance or HR group
    is_finance = request.user.groups.filter(name='Finance').exists()
    is_hr = request.user.groups.filter(name='HR').exists()
    
    if not (is_finance or is_hr or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access finance leaves.')
        return redirect('hr:leave_dashboard')
    
    # Get approved leaves that haven't been processed for payroll
    leaves_for_payroll = LeaveRequest.objects.filter(
        status='approved',
        payroll_processed=False
    ).order_by('start_date')
    
    # Get processed leaves for reference
    processed_leaves = LeaveRequest.objects.filter(
        payroll_processed=True
    ).order_by('-approved_date')[:20]
    
    # Calculate unpaid leaves count
    unpaid_leaves_count = 0
    for leave in leaves_for_payroll:
        if not getattr(leave, 'is_paid_leave', True):  # Check if it's unpaid
            unpaid_leaves_count += 1
    
    context = {
        'leaves_for_payroll': leaves_for_payroll,
        'processed_leaves': processed_leaves,
        'unpaid_leaves_count': unpaid_leaves_count,  # Add this
    }
    return render(request, 'hr/finance_leaves.html', context)

@login_required
def mark_payroll_processed(request, leave_id):
    """Mark a leave as processed for payroll"""
    # Check if user is in Finance or HR group
    is_finance = request.user.groups.filter(name='Finance').exists()
    is_hr = request.user.groups.filter(name='HR').exists()
    
    if not (is_finance or is_hr or request.user.is_superuser):
        messages.error(request, 'You do not have permission to process payroll.')
        return redirect('hr:leave_dashboard')
    
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    if request.method == 'POST':
        leave.payroll_processed = True
        leave.payroll_remarks = request.POST.get('payroll_remarks', '')
        leave.save()
        
        # Audit log
        audit_log(
            user=request.user,
            action='UPDATE',
            module='HR-Leave-Payroll',
            object_type='LeaveRequest',
            object_id=leave.id,
            description=sanitize_audit_text(f'Marked leave as payroll processed for {leave.employee.full_name}'),
            old_values={'payroll_processed': False},
            new_values={'payroll_processed': True},
            request=request
        )
        
        messages.success(request, 'Leave marked as payroll processed!')
    
    return redirect('hr:finance_leaves_view')

@login_required
def leave_cancel(request, leave_id):
    """Employee cancels their own leave request if still pending"""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    # Check if user owns this leave
    try:
        employee = request.user.employee
    except:
        messages.error(request, 'You need an employee record to cancel leaves.')
        return redirect('hr:my_leave_requests')
    
    if leave.employee != employee:
        messages.error(request, 'You can only cancel your own leave requests.')
        return redirect('hr:my_leave_requests')
    
    if leave.status != 'pending':
        messages.error(request, 'Only pending leave requests can be cancelled.')
        return redirect('hr:my_leave_requests')
    
    if request.method == 'POST':
        old_status = leave.status
        leave.status = 'cancelled'
        leave.save()
        
        # Audit log
        audit_log(
            user=request.user,
            action='CANCEL',
            module='HR-Leave',
            object_type='LeaveRequest',
            object_id=leave.id,
            description=sanitize_audit_text(f'Cancelled own leave request'),
            old_values={'status': old_status},
            new_values={'status': 'cancelled'},
            request=request
        )
        
        messages.success(request, 'Leave request cancelled successfully.')
        return redirect('hr:my_leave_requests')
    
    context = {'leave': leave}
    return render(request, 'hr/leave_cancel_confirm.html', context)

@login_required
@group_required('HR')
def export_leaves_pdf(request):
    """Export all leaves to professional PDF report"""
    # Get filtered leaves
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    leaves = LeaveRequest.objects.all().select_related('employee', 'leave_type').order_by('-submitted_date')
    
    if status_filter:
        leaves = leaves.filter(status=status_filter)
    if department_filter:
        leaves = leaves.filter(employee__department=department_filter)
    
    # Create buffer
    buffer = io.BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        title="Leave Requests Report"
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Company Header
    company_info = """
    <para align=center>
    <font size=18 color=#2E86AB><b>CORNELL SIMBA ENTERPRISES</b></font><br/>
    <font size=12 color=#5D5D5D>Human Resources Department</font><br/>
    <font size=10 color=#777777>Leave Management System</font>
    </para>
    """
    elements.append(Paragraph(company_info, styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Report Title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2E86AB'),
        spaceAfter=30
    )
    elements.append(Paragraph("LEAVE REQUESTS REPORT", title_style))
    
    # Report Details
    details = f"""
    <para>
    <font size=10>
    <b>Report Date:</b> {timezone.now().strftime('%B %d, %Y')}<br/>
    <b>Generated By:</b> {request.user.get_full_name() or request.user.username}<br/>
    <b>Total Records:</b> {leaves.count()}
    </font>
    </para>
    """
    elements.append(Paragraph(details, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Filters Section
    if status_filter or department_filter:
        filter_details = "<b>Applied Filters:</b> "
        if status_filter:
            filter_details += f"Status: {status_filter.title()} "
        if department_filter:
            filter_details += f"Department: {department_filter}"
        elements.append(Paragraph(filter_details, styles['Normal']))
        elements.append(Spacer(1, 15))
    
    # Statistics
    approved = leaves.filter(status='approved').count()
    pending = leaves.filter(status='pending').count()
    rejected = leaves.filter(status='rejected').count()
    cancelled = leaves.filter(status='cancelled').count()
    
    stats = f"""
    <para>
    <font size=10>
    <b>Approved:</b> {approved} | 
    <b>Pending:</b> {pending} | 
    <b>Rejected:</b> {rejected} |
    <b>Cancelled:</b> {cancelled}
    </font>
    </para>
    """
    elements.append(Paragraph(stats, styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Table Data
    table_data = [
        ['ID', 'Employee', 'Department', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Status']
    ]
    
    for leave in leaves:
        table_data.append([
            str(leave.id),
            leave.employee.full_name[:20] if leave.employee and leave.employee.full_name else 'N/A',
            leave.employee.department if leave.employee else 'N/A',
            leave.leave_type.name[:15] if leave.leave_type else 'N/A',
            leave.start_date.strftime('%m/%d/%y') if leave.start_date else 'N/A',
            leave.end_date.strftime('%m/%d/%y') if leave.end_date else 'N/A',
            str(leave.days_requested),
            leave.status.title() if leave.status else 'N/A'
        ])
    
    # Create table
    table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch, 1*inch, 0.5*inch, 0.8*inch])
    
    # Table styling
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DEE2E6')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 40))
    
    # Footer
    footer = f"""
    <para align=center>
    <font size=8 color=#777777>
    Report generated on {timezone.now().strftime('%Y-%m-%d at %H:%M:%S')}<br/>
    Cornell Simba Enterprises - Confidential Document
    </font>
    </para>
    """
    elements.append(Paragraph(footer, styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    # Prepare response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"leave_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    # Audit log
    audit_log(
        user=request.user,
        action='EXPORT',
        module='HR-Leave',
        object_type='LeaveRequest',
        object_id=None,
        description=sanitize_audit_text(f'Exported {leaves.count()} leaves to PDF report'),
        request=request
    )
    
    return response

@login_required
@group_required('HR')
def send_leave_reminders(request):
    """Send reminder emails about pending leaves"""
    if request.method == 'POST':
        pending_count = LeaveRequest.objects.filter(status='pending').count()
        
        # For now, just log it
        messages.info(request, f'Reminder functionality coming soon. There are {pending_count} pending leave requests.')
        
        # Audit log
        audit_log(
            user=request.user,
            action='REMINDER',
            module='HR-Leave',
            object_type='LeaveRequest',
            object_id=None,
            description=sanitize_audit_text(f'Sent reminders for {pending_count} pending leaves'),
            request=request
        )
        
        return redirect('hr:hr_leave_management')
    else:
        return redirect('hr:hr_leave_management')
    
@login_required
@group_required('Finance')
def payroll_dashboard(request):
    """Payroll dashboard for finance users"""
    context = {
        'title': 'Payroll Dashboard',
    }
    return render(request, 'hr/payroll_dashboard.html', context)

@login_required
@group_required('Finance')
def process_payroll(request):
    """Process payroll"""
    if request.method == 'POST':
        # Add your payroll processing logic here
        messages.success(request, 'Payroll processed successfully.')
        return redirect('hr:payroll_dashboard')
    
    context = {'title': 'Process Payroll'}
    return render(request, 'hr/process_payroll.html', context)

@login_required
@group_required('Finance')
def payroll_history(request):
    """View payroll history"""
    context = {'title': 'Payroll History'}
    return render(request, 'hr/payroll_history.html', context)