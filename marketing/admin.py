from django.contrib import admin
from .models import Customer, Contract, Sale
from django.utils.html import format_html

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'contact_person', 'phone', 'is_active', 'created_at')
    list_filter = ('customer_type', 'is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'customer_type', 'contact_person', 'phone', 'email')
        }),
        ('Address & Legal', {
            'fields': ('address', 'tin_number')
        }),
        ('Financial', {
            'fields': ('credit_limit', 'payment_terms')
        }),
        ('Status & Dates', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'customer', 'contract_type', 'status', 'start_date', 'end_date', 'value', 'account_manager', 'is_active_display')
    list_filter = ('contract_type', 'status', 'start_date', 'end_date')
    search_fields = ('contract_number', 'customer__name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'days_remaining', 'total_sales_value', 'sales_count')
    fieldsets = (
        ('Contract Information', {
            'fields': ('contract_number', 'customer', 'contract_type', 'description')
        }),
        ('Dates & Value', {
            'fields': ('start_date', 'end_date', 'value', 'renewal_date')
        }),
        ('Management', {
            'fields': ('account_manager', 'status', 'payment_terms', 'notes')
        }),
        ('Calculations', {
            'fields': ('is_active_display', 'days_remaining', 'total_sales_value', 'sales_count')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = 'Active'
    
    def days_remaining(self, obj):
        return obj.days_remaining
    days_remaining.short_description = 'Days Remaining'


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'contract', 'sale_type', 'total_price', 'sale_date', 'payment_status', 'payment_status_badge', 'is_overdue_display', 'sales_person')  # ADDED 'payment_status' HERE
    list_filter = ('sale_type', 'payment_status', 'sale_date', 'sales_person')
    search_fields = ('invoice_number', 'contract__contract_number', 'item_description')
    readonly_fields = ('created_at', 'updated_at', 'total_price', 'days_overdue')
    list_editable = ('payment_status',)  # Now 'payment_status' is in list_display
    
    def payment_status_badge(self, obj):
        colors = {
            'Pending': '#6c757d',
            'Partial': '#17a2b8',
            'Paid': '#28a745',
            'Overdue': '#dc3545',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.85em;">{}</span>',
            color, obj.payment_status
        )
    payment_status_badge.short_description = 'Status Badge'  # Different from 'payment_status'
    
    def is_overdue_display(self, obj):
        return obj.is_overdue
    is_overdue_display.boolean = True
    is_overdue_display.short_description = 'Overdue'
    
    def total_price(self, obj):
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total Price'