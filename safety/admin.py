from django.contrib import admin
from .models import SafetyIncident, SafetyInspection

@admin.register(SafetyIncident)
class SafetyIncidentAdmin(admin.ModelAdmin):
    list_display = ('incident_id', 'title', 'severity', 'location', 'is_resolved')
    list_filter = ('severity', 'is_resolved')
    search_fields = ('incident_id', 'title')


@admin.register(SafetyInspection)
class SafetyInspectionAdmin(admin.ModelAdmin):
    list_display = ('inspection_id', 'area', 'inspection_date', 'compliant')
    list_filter = ('compliant',)
