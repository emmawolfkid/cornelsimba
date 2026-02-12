from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [

    # ================= DASHBOARD =================
    path('', views.sales_dashboard, name='dashboard'),
    path('no-access/', views.no_access, name='no_access'),

    # ================= CUSTOMERS =================
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # ================= SALES =================
    path('list/', views.sale_list, name='sale_list'),
    path('create/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/edit/', views.sale_create, name='sale_edit'),
    path('<int:pk>/delete/', views.sale_delete, name='sale_delete'),

    # ================= SALE ACTIONS =================
    path('<int:pk>/approve/', views.sale_approve, name='sale_approve'),
    path('<int:pk>/request-stock-out/', views.request_stock_out, name='request_stock_out'),
    path('<int:pk>/mark-completed/', views.sale_mark_completed, name='sale_mark_completed'),
    path('<int:pk>/cancel/', views.sale_cancel, name='sale_cancel'),
    path('<int:pk>/check-stock/', views.check_stock_availability, name='check_stock_availability'),
    path('<int:pk>/add-payment/', views.sale_add_payment, name='sale_add_payment'),
    path('<int:pk>/stock-out-status/', views.view_stock_out_status, name='view_stock_out_status'),

    # ================= PAYMENTS =================
    path('payments/', views.payment_list, name='payment_list'),

    # ================= REPORTS =================
    path('reports/', views.sales_report, name='sales_report'),
    path('reports/sale-items/', views.sale_items_report, name='sale_items_report'),
    path('download-pdf/', views.download_sales_pdf, name='download_sales_pdf'),

    # ================= STOCK OUT =================
    path('stock-outs/pending/', views.pending_stock_outs, name='pending_stock_outs'),
]
