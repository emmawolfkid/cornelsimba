# cornelsimba/inventory/admin.py
from django.contrib import admin
from .models import Item, StockIn, StockOut, StockAdjustment, StockHistory

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'unit_of_measure', 'status']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):
    list_display = ['item', 'quantity', 'source', 'status', 'date']
    list_filter = ['status', 'source', 'date']
    search_fields = ['item__name', 'reference']
    readonly_fields = ['created_at', 'approved_at', 'date']
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete stock records
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        # Managers can edit pending records
        if obj and obj.status == 'pending':
            return request.user.groups.filter(name='Manager').exists() or request.user.is_superuser
        return request.user.is_superuser

@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ['item', 'quantity', 'purpose', 'status', 'date']
    list_filter = ['status', 'purpose', 'date']
    search_fields = ['item__name', 'reference']
    readonly_fields = ['created_at', 'approved_at', 'date']
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'pending':
            return request.user.groups.filter(name='Manager').exists() or request.user.is_superuser
        return request.user.is_superuser

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['item', 'adjustment_quantity', 'adjustment_type', 'status', 'created_at']
    list_filter = ['status', 'adjustment_type']
    search_fields = ['item__name', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'requested_at', 'approved_at', 'rejected_at']
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ['item', 'transaction_type', 'quantity', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['item__name', 'reference']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    