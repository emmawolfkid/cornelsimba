from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  


app_name = 'dashboard'

urlpatterns = [
    path('', views.main_dashboard, name='main'),
   path('accounts/login/', auth_views.LogoutView.as_view(next_page='login'), name='login'),
]
