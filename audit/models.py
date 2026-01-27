from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AuditLog(models.Model):
    # Module choices
    MODULE_CHOICES = [
        ('SALES', 'Sales'),
        ('FINANCE', 'Finance'),
        ('INVENTORY', 'Inventory'),
        ('HR', 'HR'),
        ('PROCUREMENT', 'Procurement'),
        ('MARKETING', 'Marketing'),
        ('SAFETY', 'Safety'),
        ('DASHBOARD', 'Dashboard'),
        ('AUTH', 'Authentication'),
        ('OTHER', 'Other'),
    ]

    # Action choices
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('EXPORT', 'Export'),
        ('ACCESS_DENIED', 'Access Denied'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True
    )

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_index=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)

    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    browser_info = models.CharField(max_length=255, blank=True)

    # Old and new values (for updates)
    old_values = models.TextField(blank=True)
    new_values = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.user} - {self.action} - {self.module} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
