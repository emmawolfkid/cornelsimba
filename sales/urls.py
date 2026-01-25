# cornelsimba/sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.sales_dashboard, name='dashboard'),
    path('no-access/', views.no_access, name='no_access'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Sales
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/create/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/edit/', views.sale_create, name='sale_edit'),
    path('sales/<int:pk>/delete/', views.sale_delete, name='sale_delete'),
    
    # Sale Actions
    path('sales/<int:pk>/approve/', views.sale_approve, name='sale_approve'),
    path('sales/<int:pk>/request-stock-out/', views.request_stock_out, name='request_stock_out'),
    path('sales/<int:pk>/mark-completed/', views.sale_mark_completed, name='sale_mark_completed'),
    path('sales/<int:pk>/cancel/', views.sale_cancel, name='sale_cancel'),
    path('sales/<int:pk>/check-stock/', views.check_stock_availability, name='check_stock_availability'),
    
    # Payments
    path('sales/<int:pk>/add-payment/', views.sale_add_payment, name='sale_add_payment'),
    path('payments/', views.payment_list, name='payment_list'),
    
    # Reports - ADD THESE TWO LINES:
    path('reports/', views.sales_report, name='sales_report'),  # This is the correct one
    path('report/', views.sales_report, name='report'),  # Add alias for compatibility
    
    # OR just rename to 'report' if you want:
    # path('reports/', views.sales_report, name='report'),
    
    # Additional reports
    path('reports/sale-items/', views.sale_items_report, name='sale_items_report'),
    
    # Stock Out Management
    path('stock-outs/pending/', views.pending_stock_outs, name='pending_stock_outs'),
    path('sales/<int:pk>/stock-out-status/', views.view_stock_out_status, name='view_stock_out_status'),
    # Stock out status URL
    path('sales/<int:pk>/stock-out-status/', views.view_stock_out_status, name='view_stock_out_status'),

    path('download-pdf/', views.download_sales_pdf, name='download_sales_pdf'),
]