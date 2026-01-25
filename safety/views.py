from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import SafetyIncident, SafetyInspection

def safety_access_required(view_func):
    def wrapper(request, *args, **kwargs):
        if (
            request.user.groups.filter(name__in=['Safety Officer', 'Manager']).exists()
            or request.user.is_superuser
        ):
            return view_func(request, *args, **kwargs)
        return redirect('/')
    return wrapper
@login_required
@safety_access_required
def safety_dashboard(request):
    incidents = SafetyIncident.objects.all().order_by('-date_reported')
    inspections = SafetyInspection.objects.all().order_by('-inspection_date')

    return render(request, 'safety/dashboard.html', {
        'incidents': incidents,
        'inspections': inspections
    })
