# cornelsimba/marketing/urls.py - UPDATED
from django.urls import path
from django.shortcuts import redirect  # ADD THIS IMPORT
from . import views

app_name = 'marketing'

urlpatterns = [
    # Dashboard
    path('', views.marketing_dashboard, name='dashboard'),
    
    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/edit/', views.client_update, name='client_update'),
    
    # Contracts (using /campaigns/ URLs for compatibility)
    path('campaigns/', views.contract_list, name='contract_list'),
    path('campaigns/<int:pk>/', views.contract_detail, name='contract_detail'),
    path('campaigns/add/', views.contract_create, name='contract_create'),
    path('campaigns/<int:pk>/edit/', views.contract_update, name='contract_update'),
    
    # Sales (using /leads/ URLs for compatibility)
    path('leads/', views.sale_list, name='sale_list'),
    path('leads/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('leads/add/', views.sale_create, name='sale_create'),
    path('leads/<int:pk>/edit/', views.sale_update, name='sale_update'),
    
    # Reports
    path('reports/sales/', views.sales_report, name='sales_report'),
]