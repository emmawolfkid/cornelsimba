from .models import AuditLog
from django.contrib.auth.models import AnonymousUser
import json

def audit_log(user, action, module, description, 
              object_type='', object_id='', 
              old_values=None, new_values=None,
              request=None):
    """
    Simple function to create audit logs
    """
    # Handle anonymous users
    if isinstance(user, AnonymousUser):
        user = None
    
    # Convert old/new values to JSON strings if they're dicts/lists
    old_values_str = ''
    new_values_str = ''
    
    if old_values is not None:
        if isinstance(old_values, (dict, list)):
            old_values_str = json.dumps(old_values, default=str)
        else:
            old_values_str = str(old_values)
    
    if new_values is not None:
        if isinstance(new_values, (dict, list)):
            new_values_str = json.dumps(new_values, default=str)
        else:
            new_values_str = str(new_values)
    
    # Get IP and browser info from request
    ip_address = None
    browser_info = ''
    
    if request:
        ip_address = get_client_ip(request)
        browser_info = request.META.get('HTTP_USER_AGENT', '')[:255]
    
    # Create the audit log
    AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_type=object_type,
        object_id=str(object_id),
        description=description,
        old_values=old_values_str,
        new_values=new_values_str,
        ip_address=ip_address,
        browser_info=browser_info
    )

def get_client_ip(request):
    """
    Get the client's IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip