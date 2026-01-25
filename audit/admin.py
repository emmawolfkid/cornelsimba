from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'module', 'object_type', 'timestamp')
    list_filter = ('action', 'module', 'timestamp', 'user')
    search_fields = ('user__username', 'description', 'object_type')
    readonly_fields = ('timestamp', 'user', 'action', 'module', 'object_type', 
                      'object_id', 'description', 'ip_address', 'browser_info',
                      'old_values', 'new_values')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Don't allow adding logs manually
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superuser can delete