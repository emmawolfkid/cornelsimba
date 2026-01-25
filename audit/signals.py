from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .utils import audit_log

# Track user login
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    audit_log(
        user=user,
        action='LOGIN',
        module='AUTH',
        description=f'User {user.username} logged in successfully',
        request=request
    )

# Track user logout
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    audit_log(
        user=user,
        action='LOGOUT',
        module='AUTH',
        description=f'User {user.username} logged out',
        request=request
    )