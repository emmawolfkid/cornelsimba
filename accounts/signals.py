from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from audit.utils import log_action

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    log_action(
        user=user,
        action='LOGIN',
        module='Authentication',
        description='User logged in'
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    log_action(
        user=user,
        action='LOGOUT',
        module='Authentication',
        description='User logged out'
    )
