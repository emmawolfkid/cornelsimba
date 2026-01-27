from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'hr'

urlpatterns = [
    # Dashboard
    path('', views.hr_dashboard, name='hr_dashboard'),

    # Employees
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_create, name='employee_create'),
    path('employees/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:employee_id>/edit/', views.employee_update, name='employee_update'),
    path('employees/<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),

    # Users sync
    path('sync-users/', views.user_sync_view, name='user_sync'),
    path('create-from-user/<int:user_id>/', views.create_employee_from_user, name='create_from_user'),

    # Leave
    path('leave/', views.leave_dashboard, name='leave_dashboard'),
    path('leave/request/', views.leave_request_create, name='leave_request_create'),
    path('leave/my-requests/', views.my_leave_requests, name='my_leave_requests'),
    path('leave/<int:leave_id>/', views.leave_request_detail, name='leave_detail'),
    path('leave/<int:leave_id>/cancel/', views.leave_cancel, name='leave_cancel'),

    # Leave approvals
    path('leave/approvals/', views.leave_approval_list, name='leave_approval_list'),
    path('leave/<int:leave_id>/approve/', views.leave_approve_reject, name='leave_approve_reject'),

    # HR leave management
    path('leave/all/', views.hr_leave_management, name='hr_leave_management'),
    path('leave/<int:leave_id>/edit/', views.hr_leave_edit, name='hr_leave_edit'),
    path('leave/hr/add/', views.hr_leave_add, name='hr_leave_add'),

    # Finance + leave
    path('leave/finance/', views.finance_leaves_view, name='finance_leaves_view'),
    path('leave/<int:leave_id>/payroll-processed/', views.mark_payroll_processed, name='mark_payroll_processed'),

    # Leave utilities
    path('leave/export/pdf/', views.export_leaves_pdf, name='export_leaves_pdf'),
    path('leave/send-reminders/', views.send_leave_reminders, name='send_leave_reminders'),

    # Payroll (HR-side)
    path('payroll/', views.payroll_dashboard, name='payroll_dashboard'),
    path('payroll/process/', views.process_payroll, name='process_payroll'),
    path('payroll/history/', views.payroll_history, name='payroll_history'),
]

# Only add static files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)