# cornelsimba/sales/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, Sale, SaleItem, Payment, SaleReturn

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_type', 'contact_person', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['customer_type', 'is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email', 'tax_id']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'customer_type', 'contact_person', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'address')
        }),
        ('Business Information', {
            'fields': ('tax_id', 'credit_limit', 'payment_terms', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'customer', 'net_amount_display', 'status_badge', 'sale_date', 'is_paid_display']
    list_filter = ['status', 'sale_type', 'sale_date', 'is_paid']
    search_fields = ['sale_number', 'customer__name', 'stock_out__reference']
    readonly_fields = ['created_at', 'updated_at', 'sale_number']
    date_hierarchy = 'sale_date'
    actions = ['mark_as_completed', 'mark_as_cancelled']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'customer', 'sale_type', 'status', 'sale_date')
        }),
        ('Pricing', {
            'fields': ('total_amount', 'tax_amount', 'discount_amount', 'net_amount')
        }),
        ('Payment Status', {
            'fields': ('amount_paid', 'balance_due', 'is_paid')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'delivery_date', 'delivery_status')
        }),
        ('Integration', {
            'fields': ('stock_out',)
        }),
        ('Notes', {
            'fields': ('notes', 'terms_conditions')
        }),
        ('Audit Trail', {
            'fields': ('created_by', 'approved_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def net_amount_display(self, obj):
        return f"${obj.net_amount:,.2f}"
    net_amount_display.short_description = 'Net Amount'
    net_amount_display.admin_order_field = 'net_amount'
    
    def is_paid_display(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green; font-weight: bold;">✓ Paid</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">● Due: ${}</span>', obj.balance_due)
    is_paid_display.short_description = 'Payment Status'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'PENDING': '#ffc107',
            'APPROVED': '#17a2b8',
            'COMPLETED': '#28a745',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.85em;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} sale(s) marked as completed.')
    mark_as_completed.short_description = "Mark selected sales as completed"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} sale(s) marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected sales as cancelled"


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['total_price', 'tax_amount']
    fields = ['item', 'quantity', 'unit_price', 'tax_rate', 'total_price', 'tax_amount']
    can_delete = True
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "item":
            # Only show active items
            kwargs["queryset"] = SaleItem._meta.get_field('item').related_model.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'item', 'quantity', 'unit_price_display', 'total_price_display', 'created_at']
    list_filter = ['sale__sale_date', 'item']
    search_fields = ['sale__sale_number', 'item__name']
    readonly_fields = ['total_price', 'tax_amount', 'created_at']
    
    def unit_price_display(self, obj):
        return f"${obj.unit_price:,.2f}"
    unit_price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return f"${obj.total_price:,.2f}"
    total_price_display.short_description = 'Total Price'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['sale', 'amount_display', 'payment_method', 'payment_status_badge', 'payment_date', 'reference_number']
    list_filter = ['payment_method', 'payment_status', 'payment_date']
    search_fields = ['sale__sale_number', 'reference_number', 'cheque_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    
    def amount_display(self, obj):
        return f"${obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def payment_status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'COMPLETED': '#28a745',
            'FAILED': '#dc3545',
            'REFUNDED': '#6c757d',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.85em;">{}</span>',
            color, obj.payment_status
        )
    payment_status_badge.short_description = 'Status'


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ['return_number', 'original_sale', 'reason', 'refund_amount_display', 'refund_status_badge', 'created_at']
    list_filter = ['reason', 'refund_status', 'created_at']
    search_fields = ['return_number', 'original_sale__sale_number']
    readonly_fields = ['created_at', 'updated_at', 'return_number']
    actions = ['approve_refunds', 'reject_refunds']
    
    def refund_amount_display(self, obj):
        return f"${obj.refund_amount:,.2f}"
    refund_amount_display.short_description = 'Refund Amount'
    
    def refund_status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'APPROVED': '#17a2b8',
            'REFUNDED': '#28a745',
            'REJECTED': '#dc3545',
        }
        color = colors.get(obj.refund_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.85em;">{}</span>',
            color, obj.refund_status
        )
    refund_status_badge.short_description = 'Status'
    
    def approve_refunds(self, request, queryset):
        updated = queryset.update(refund_status='APPROVED')
        self.message_user(request, f'{updated} return(s) approved.')
    approve_refunds.short_description = "Approve selected returns"
    
    def reject_refunds(self, request, queryset):
        updated = queryset.update(refund_status='REJECTED')
        self.message_user(request, f'{updated} return(s) rejected.')
    reject_refunds.short_description = "Reject selected returns"


# Optional: Add Sale items inline to Sale admin
class SaleAdminWithItems(SaleAdmin):
    inlines = [SaleItemInline]

# Re-register Sale with inline items
admin.site.unregister(Sale)
admin.site.register(Sale, SaleAdminWithItems)