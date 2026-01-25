from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_logs, name='audit_logs'),
    path('<int:log_id>/', views.audit_log_detail, name='audit_log_detail'),
    # Note: The export and download functionality is now handled within 
    # the main views using GET parameters
]