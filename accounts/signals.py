from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from audit.utils import audit_log
from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
   audit_log(
        user=user,
        action='LOGIN',
        module='Authentication',
        description='User logged in'
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    audit_log(
        user=user,
        action='LOGOUT',
        module='Authentication',
        description='User logged out'
    )

# 👇 your system-wide groups (CONSTANT)
DEFAULT_GROUPS = [
    'Admin',
    'Manager',
    'HR',
    'Finance',
    'Inventory',
    'Procurement',
    'Sales',
    'Auditor',
]

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    for group_name in DEFAULT_GROUPS:
        Group.objects.get_or_create(name=group_name)