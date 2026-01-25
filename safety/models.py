from django.db import models
from hr.models import Employee

class SafetyIncident(models.Model):
    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Fatal', 'Fatal'),
    ]

    incident_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=100)

    reported_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    date_reported = models.DateTimeField(auto_now_add=True)

    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.incident_id


class SafetyInspection(models.Model):
    inspection_id = models.CharField(max_length=20, unique=True)
    inspector = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)

    area = models.CharField(max_length=100)
    findings = models.TextField()
    action_required = models.TextField()

    inspection_date = models.DateField()
    compliant = models.BooleanField(default=False)

    def __str__(self):
        return self.inspection_id
