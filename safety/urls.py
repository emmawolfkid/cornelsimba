from django.urls import path
from . import views

app_name = 'safety'

urlpatterns = [
    path('', views.safety_dashboard, name='safety_dashboard'),  # Empty string
]