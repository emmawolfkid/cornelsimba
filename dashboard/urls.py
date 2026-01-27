from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  


app_name = 'dashboard'

urlpatterns = [
    path('', views.main_dashboard, name='main'),
  
]
