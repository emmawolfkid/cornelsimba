# inventory/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'inventory'

urlpatterns = [
    # Dashboard URLs
    path('', views.inventory_dashboard, name='inventory_dashboard'),
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    
    # Items
    path('items/', views.item_list, name='item_list'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('items/<int:pk>/update/', views.item_update, name='item_update'),
    
    # Stock Ins
    path('stock-ins/', views.stock_in_list, name='stock_in_list'),
    path('stock-ins/create/', views.stock_in_create, name='stock_in_create'),
    path('stock-ins/<int:pk>/edit/', views.stock_in_edit, name='stock_in_edit'),
    path('stock-ins/<int:pk>/', views.stock_in_detail, name='stock_in_detail'),
    
    # Stock Outs
    path('stock-outs/', views.stock_out_list, name='stock_out_list'),
    path('stock-outs/create/', views.stock_out_create, name='stock_out_create'),
    path('stock-outs/<int:pk>/', views.stock_out_detail, name='stock_out_detail'),
    path('stock-outs/<int:pk>/edit/', views.stock_out_edit, name='stock_out_edit'),
    
    # Stock Out Approval URLs - ADD THESE
    path('stock-outs/<int:pk>/approve/', views.approve_stockout, name='approve_stockout'),
    path('stock-outs/<int:pk>/reject/', views.reject_stockout, name='reject_stockout'),
    
    # Adjustments
    path('adjustments/', views.stock_adjustment_list, name='adjustment_list'),
    path('adjustments/create/', views.stock_adjustment_create, name='adjustment_create'),
    path('adjustments/<int:pk>/', views.adjustment_detail, name='adjustment_detail'),
    path('adjustments/<int:pk>/approve/', views.stock_adjustment_approve, name='adjustment_approve'),
    
    # Reports
    path('reports/', views.stock_report, name='stock_report'),
    path('procurement/', views.procurement_stock, name='procurement_stock'),
    
    # Sales Integration
    path('pending-sales-stockouts/', views.pending_sales_stockouts, name='pending_sales_stockouts'),

    path('api/item/<int:pk>/', views.get_item_details, name='item_details_api'),

    path('accounts/login/', auth_views.LogoutView.as_view(next_page='login'), name='login'),
]