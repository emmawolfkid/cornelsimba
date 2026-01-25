from django.urls import path
from . import views

app_name = 'procurement'

urlpatterns = [
    # Dashboard
    path('', views.procurement_dashboard, name='dashboard'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    
    # Purchase Orders
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/add/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/edit/', views.purchase_order_update, name='purchase_order_update'),
    path('purchase-orders/<int:pk>/approve/', views.purchase_order_approve, name='purchase_order_approve'),
    path('purchase-orders/<int:pk>/cancel/', views.purchase_order_cancel, name='purchase_order_cancel'),
    
    # Delivery (kept for backward compatibility)
    path('deliver/<int:order_id>/', views.mark_delivered, name='mark_delivered'),
    
    # Finance Integration
    path('finance/purchase-orders/', views.finance_purchase_orders, name='finance_purchase_orders'),
    path('finance/purchase-orders/<int:pk>/expense/', views.po_to_expense, name='po_to_expense'),
]