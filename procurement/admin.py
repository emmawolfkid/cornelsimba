from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'email')
    list_editable = ('is_active',)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'requested_by', 'status', 'total_amount', 'order_date')
    list_filter = ('status', 'department', 'order_date')
    search_fields = ('po_number', 'supplier__name', 'requested_by__full_name')
    readonly_fields = ('po_number', 'total_amount', 'created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('po_number', 'supplier', 'status', 'total_amount')
        }),
        ('HR & Approval', {
            'fields': ('requested_by', 'approved_by', 'department')
        }),
        ('Finance Details', {
            'fields': ('cost_center', 'budget_code', 'notes')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery', 'created_at', 'updated_at')
        }),
    )