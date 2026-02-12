# cornelsimba/sales/views.py - FULLY UPDATED AND CORRECTED VERSION
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from functools import wraps
from decimal import Decimal
from django.core.exceptions import ValidationError
import json

from .models import Customer, Sale, SaleItem, Payment
from .forms import CustomerForm, SaleForm, SaleItemFormSet, PaymentForm
from inventory.models import Item
from audit.utils import audit_log

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from reportlab.lib import colors


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
    
@login_required
def no_access(request):
    """View for users who don't have access to certain pages"""
    return render(request, 'sales/no_access.html')

def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('sales:dashboard')
        return _wrapped_view
    return decorator

@login_required
@group_required('Sales')
def sales_dashboard(request):
    """Sales dashboard with overview"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    one_week_ago = today - timedelta(days=7)
    
    # Sales statistics
    total_sales = Sale.objects.filter(status='COMPLETED').count()
    monthly_sales = Sale.objects.filter(
        status='COMPLETED',
        sale_date__gte=start_of_month
    ).count()
    weekly_sales = Sale.objects.filter(
        status='COMPLETED',
        sale_date__gte=one_week_ago
    ).count()
    
    # Revenue statistics - IN TSH
    total_revenue = Sale.objects.filter(status='COMPLETED').aggregate(
        total=Sum('net_amount')
    )['total'] or Decimal('0')
    
    monthly_revenue = Sale.objects.filter(
        status='COMPLETED',
        sale_date__gte=start_of_month
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    weekly_revenue = Sale.objects.filter(
        status='COMPLETED',
        sale_date__gte=one_week_ago
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    # Stock out status counts
    pending_stock_out = Sale.objects.filter(
        status='STOCK_OUT_PENDING'
    ).count()
    
    # CORRECT: Filter by related field, not property
    approved_stock_out = Sale.objects.filter(
        inventory_stock_out__isnull=False,
        inventory_stock_out__status='approved'
    ).count()
    
    # Recent sales
    recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:10]
    
    # Top customers
    top_customers = Sale.objects.filter(status='COMPLETED').values(
        'customer__name'
    ).annotate(
        total_sales=Count('id'),
        total_amount=Sum('net_amount')
    ).order_by('-total_amount')[:5]
    
    # Sales requiring attention
    pending_approval = Sale.objects.filter(status='PENDING').count()
    
    # ✅ ADD THESE LINES FOR DASHBOARD:
    pending_sales = Sale.objects.filter(status='PENDING').count()
    customers_count = Customer.objects.filter(is_active=True).count()
    
    context = {
        'total_sales': total_sales,
        'monthly_sales': monthly_sales,
        'weekly_sales': weekly_sales,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'weekly_revenue': weekly_revenue,
        'pending_stock_out': pending_stock_out,
        'approved_stock_out': approved_stock_out,
        'pending_approval': pending_approval,
        'recent_sales': recent_sales,
        'top_customers': top_customers,
        'today': today,
        'pending_sales': pending_sales,  # ✅ Add this
        'customers_count': customers_count,  # ✅ Add this
    }
    
    return render(request, 'sales/dashboard.html', context)

@login_required
@group_required('Sales')
def customer_list(request):
    """List all customers"""
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    search_query = request.GET.get('search')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'customers': customers,
    }
    return render(request, 'sales/customer_list.html', context)

@login_required
@group_required('Sales')
def customer_detail(request, pk):
    """Customer details with sales history"""
    customer = get_object_or_404(Customer, pk=pk)
    
    sales = customer.sales.all().order_by('-created_at')[:20]
    total_sales = customer.sales.filter(status='COMPLETED').count()
    total_revenue = customer.sales.filter(status='COMPLETED').aggregate(
        total=Sum('net_amount')
    )['total'] or Decimal('0')
    
    # Pending payments
    pending_payments = Decimal('0')
    for sale in customer.sales.filter(status='COMPLETED', is_paid=False):
        pending_payments += sale.balance_due
    
    # Prepare messages for JSON
    django_messages = []
    for message in messages.get_messages(request):
        django_messages.append({
            'message': str(message),
            'tags': message.tags
        })
    
    context = {
        'customer': customer,
        'sales': sales,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'django_messages_json': json.dumps(django_messages),
    }
    return render(request, 'sales/customer_detail.html', context)

@login_required
@group_required('Sales')
def customer_create(request):
    """Create new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='SALES',
                object_type='Customer',
                object_id=customer.id,
                description=f'Created customer "{customer.name}"',
                request=request
            )
            
            messages.success(request, f'Customer "{customer.name}" created successfully!')
            return redirect('sales:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'sales/customer_form.html', {'form': form})

@login_required
@group_required('Sales')
def customer_edit(request, pk):
    """Edit existing customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            old_name = customer.name  # Save old name for audit
            customer = form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='UPDATE',
                module='SALES',
                object_type='Customer',
                object_id=customer.id,
                description=f'Updated customer: "{old_name}" → "{customer.name}"',
                request=request
            )
            
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('sales:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'sales/customer_form.html', {'form': form, 'customer': customer})

@login_required
@group_required('Sales')
def customer_delete(request, pk):
    """Delete customer (soft delete)"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if customer has any sales
    if customer.sales.exists():
        messages.error(request, f'Cannot delete customer "{customer.name}" because they have sales records.')
        return redirect('sales:customer_detail', pk=customer.pk)
    
    if request.method == 'POST':
        customer.is_active = False
        customer.save()
        
        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='DELETE',
            module='SALES',
            object_type='Customer',
            object_id=customer.id,
            description=f'Deleted (deactivated) customer "{customer.name}"',
            request=request
        )
        
        messages.success(request, f'Customer "{customer.name}" deactivated successfully!')
        return redirect('sales:customer_list')
    
    return render(request, 'sales/customer_confirm_delete.html', {'customer': customer})
@login_required
@group_required('Sales')
def sale_list(request):
    """List all sales"""
    sales = Sale.objects.select_related('customer').order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    customer_filter = request.GET.get('customer')
    if customer_filter:
        sales = sales.filter(customer__id=customer_filter)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        sales = sales.filter(sale_date__gte=date_from)
    if date_to:
        sales = sales.filter(sale_date__lte=date_to)
    
    # Stock out filter - FIXED: Use actual database fields
    stock_out_filter = request.GET.get('stock_out')
    if stock_out_filter == 'pending':
        sales = sales.filter(status='STOCK_OUT_PENDING')
    elif stock_out_filter == 'approved':
        sales = sales.filter(
            inventory_stock_out__isnull=False,
            inventory_stock_out__status='approved'
        )
    
    # ✅ ADD THESE 3 LINES for totals calculation
    sales_total = sales.aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    paid_total = sales.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    balance_total = sales_total - paid_total
    
    context = {
        'sales': sales,
        'status_choices': Sale.STATUS_CHOICES,
        'customers': Customer.objects.filter(is_active=True),
        'sales_total': sales_total,      # ✅ Add this
        'paid_total': paid_total,        # ✅ Add this
        'balance_total': balance_total,  # ✅ Add this
    }
    return render(request, 'sales/sale_list.html', context)

@login_required
@group_required('Sales')
@transaction.atomic
def sale_create(request, pk=None):
    """Create or edit sale with items - FIXED & BULLETPROOF"""
    sale = None
    if pk:
        sale = get_object_or_404(Sale, pk=pk)
        if sale.status != 'DRAFT':
            messages.error(request, f'Cannot edit sale in {sale.get_status_display()} status.')
            return redirect('sales:sale_detail', pk=sale.pk)
    
    if request.method == 'POST':
        sale_form = SaleForm(request.POST, instance=sale, user=request.user)
        item_formset = SaleItemFormSet(request.POST, instance=sale)
        
        if sale_form.is_valid() and item_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save sale first
                    sale = sale_form.save(commit=False)
                    if sale.pk:  # Editing
                        sale.updated_by = request.user
                    else:  # Creating
                        sale.created_by = request.user
                        sale.status = 'DRAFT'
                    
                    # Generate sale number if new
                    if not sale.sale_number:
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        sale.sale_number = f"SALE-{timestamp}"
                    
                    # Save sale to get PK
                    sale.save()
                    
                    # Process sale items
                    items = item_formset.save(commit=False)
                    
                    total_amount = Decimal('0')
                    tax_amount = Decimal('0')
                    
                    for item in items:
                        item.sale = sale
                        item.save()  # Model calculates totals with proper rounding
                        
                        total_amount += item.total_price
                        tax_amount += item.tax_amount
                    
                    # Delete removed items
                    for form in item_formset.deleted_forms:
                        if form.instance.pk:
                            form.instance.delete()
                    
                    # ✅ FIXED: Use Decimal fields directly - NO RECONVERSION
                    # These are already Decimal objects from the model
                    total_amount = Decimal(total_amount).quantize(Decimal('0.01'))
                    tax_amount = Decimal(tax_amount).quantize(Decimal('0.01'))
                    discount_amount = sale.discount_amount.quantize(Decimal('0.01'))
                    
                    # ✅ FIXED: Single calculation with proper types
                    sale.total_amount = total_amount
                    sale.tax_amount = tax_amount
                    sale.discount_amount = discount_amount
                    
                    # ✅ FIXED: Calculate net amount once, properly
                    sale.net_amount = (total_amount + tax_amount - discount_amount).quantize(Decimal('0.01'))
                    sale.balance_due = sale.net_amount  # For new sales, balance = net amount
                    
                    sale.save()
                    
                    # Audit log
                    if pk:  # Editing
                        audit_log(
                            user=request.user,
                            action='UPDATE',
                            module='SALES',
                            object_type='Sale',
                            object_id=sale.id,
                            description=f'Edited sale #{sale.sale_number}',
                            request=request
                        )
                        messages.success(request, f'Sale {sale.sale_number} updated successfully!')
                    else:  # Creating
                        audit_log(
                            user=request.user,
                            action='CREATE',
                            module='SALES',
                            object_type='Sale',
                            object_id=sale.id,
                            description=f'Created sale #{sale.sale_number} for Tsh {sale.net_amount:,.2f}',
                            request=request
                        )
                        messages.success(request, f'Sale {sale.sale_number} created successfully!')
                    
                    return redirect('sales:sale_detail', pk=sale.pk)
                    
            except Exception as e:
                messages.error(request, f'Error saving sale: {str(e)}')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        sale_form = SaleForm(instance=sale, user=request.user)
        item_formset = SaleItemFormSet(instance=sale)
    
    context = {
        'sale_form': sale_form,
        'item_formset': item_formset,
        'sale': sale,
        'title': f'Edit Sale #{sale.sale_number}' if sale else 'Create New Sale',
    }
    return render(request, 'sales/sale_form.html', context)
@login_required
@group_required('Sales')
@transaction.atomic
def sale_edit(request, pk):
    """Edit existing sale - FIXED"""
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status != 'DRAFT':
        messages.error(request, f'Cannot edit sale in {sale.get_status_display()} status.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    if request.method == 'POST':
        sale_form = SaleForm(request.POST, instance=sale, user=request.user)
        item_formset = SaleItemFormSet(request.POST, instance=sale)
        
        if sale_form.is_valid() and item_formset.is_valid():
            try:
                with transaction.atomic():
                    sale = sale_form.save(commit=False)
                    sale.updated_by = request.user
                    sale.save()
                    
                    items = item_formset.save(commit=False)
                    
                    total_amount = Decimal('0')
                    tax_amount = Decimal('0')
                    
                    for item in items:
                        item.sale = sale
                        item.save()
                        
                        total_amount += item.total_price
                        tax_amount += item.tax_amount
                    
                    for form in item_formset.deleted_forms:
                        if form.instance.pk:
                            form.instance.delete()
                    
                    # ✅ FIXED: Proper calculation without reconversion
                    total_amount = Decimal(total_amount).quantize(Decimal('0.01'))
                    tax_amount = Decimal(tax_amount).quantize(Decimal('0.01'))
                    discount_amount = sale.discount_amount.quantize(Decimal('0.01'))
                    
                    sale.total_amount = total_amount
                    sale.tax_amount = tax_amount
                    sale.discount_amount = discount_amount
                    sale.net_amount = (total_amount + tax_amount - discount_amount).quantize(Decimal('0.01'))
                    sale.balance_due = sale.net_amount
                    
                    sale.save()
                    
                    audit_log(
                        user=request.user,
                        action='UPDATE',
                        module='SALES',
                        object_type='Sale',
                        object_id=sale.id,
                        description=f'Edited sale #{sale.sale_number}',
                        request=request
                    )
                    
                    messages.success(request, f'Sale {sale.sale_number} updated successfully!')
                    return redirect('sales:sale_detail', pk=sale.pk)
                    
            except Exception as e:
                messages.error(request, f'Error updating sale: {str(e)}')
    else:
        sale_form = SaleForm(instance=sale, user=request.user)
        item_formset = SaleItemFormSet(instance=sale)
    
    context = {
        'sale_form': sale_form,
        'item_formset': item_formset,
        'sale': sale,
        'title': f'Edit Sale #{sale.sale_number}',
    }
    return render(request, 'sales/sale_form.html', context)

@login_required
@group_required('Sales')
def sale_detail(request, pk):
    """View sale details"""
    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'inventory_stock_out'),
        pk=pk
    )
    items = sale.items.select_related('item').all()
    payments = sale.payments.all()
    
    # Calculate total paid in Tsh
    total_paid = payments.filter(payment_status='COMPLETED').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # Check if we can request stock out - Use property, not database field
    can_request_stock_out = sale.can_request_stock_out
    
    # Check if sale has approved stock out - Use property
    has_approved_stock_out = sale.has_approved_stock_out
    
    can_approve_sale = sale.status == 'DRAFT'
    can_mark_completed = sale.status == 'APPROVED' and has_approved_stock_out
    
    context = {
        'sale': sale,
        'items': items,
        'payments': payments,
        'total_paid': total_paid,
        'can_request_stock_out': can_request_stock_out,
        'can_approve_sale': can_approve_sale,
        'can_mark_completed': can_mark_completed,
        'stock_out_status': sale.get_stock_out_status(),
    }
    return render(request, 'sales/sale_detail.html', context)

@login_required
@group_required('Sales')
@transaction.atomic
def sale_approve(request, pk):
    """Approve a draft sale"""
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status != 'DRAFT':
        messages.error(request, f'Sale is already {sale.get_status_display()}.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    if sale.item_count == 0:
        messages.error(request, 'Cannot approve sale with no items.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    try:
        sale.mark_as_approved(request.user)
        sale.refresh_from_db()

        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='APPROVE',
            module='SALES',
            object_type='Sale',
            object_id=sale.id,
            description=f'Approved sale #{sale.sale_number} (Amount: Tsh {sale.net_amount:,.2f})',
            request=request
        )
        
        messages.success(request, f'Sale {sale.sale_number} approved successfully!')
        messages.info(request, 'Now you can request stock out from inventory.')
        
    except Exception as e:
        messages.error(request, f'Error approving sale: {str(e)}')
    
    return redirect('sales:sale_detail', pk=sale.pk)

@login_required
@group_required('Sales')
@transaction.atomic
def request_stock_out(request, pk):
    """Request stock out for an approved sale"""
    sale = get_object_or_404(Sale, pk=pk)
    sale.refresh_from_db()
    
    # Check if sale can request stock out - Use property
    if not sale.can_request_stock_out:
        messages.error(request, f'Cannot request stock out for sale in {sale.get_status_display()} status.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    try:
        # Check stock availability
        is_available, message = sale.check_stock_availability()
        if not is_available:
            messages.error(request, f'Cannot request stock out: {message}')
            return redirect('sales:sale_detail', pk=sale.pk)
        
        # Create stock out request (pending)
        stock_out = sale.create_stock_out_request(request.user)
        
        messages.success(
            request, 
            f'Stock out request created (ID: {stock_out.id}). '
            f'Pending approval from inventory team.'
        )
        messages.info(
            request,
            'Inventory team will review and approve the stock out. '
            'Once approved, stock will be deducted and income recorded.'
        )
        
    except ValidationError as e:
        messages.error(request, f'Validation error: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error creating stock out request: {str(e)}')
    
    return redirect('sales:sale_detail', pk=sale.pk)

@login_required
@group_required('Sales')
@transaction.atomic
def sale_mark_completed(request, pk):
    """Mark sale as completed (after stock out is approved)"""
    sale = get_object_or_404(Sale, pk=pk)
    
    if not (sale.status == 'APPROVED' or sale.status == 'STOCK_OUT_PENDING'):
        messages.error(request, f'Cannot complete sale in {sale.get_status_display()} status.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    # Use property, not database field
    if not sale.has_approved_stock_out:
        messages.error(request, 'Cannot complete sale without approved stock out.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    try:
        sale.mark_as_completed(request.user)
        
        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='UPDATE',
            module='SALES',
            object_type='Sale',
            object_id=sale.id,
            description=f'Marked sale #{sale.sale_number} as COMPLETED',
            request=request
        )
        
        messages.success(request, f'Sale {sale.sale_number} marked as completed!')
        
    except Exception as e:
        messages.error(request, f'Error marking sale as completed: {str(e)}')
    
    return redirect('sales:sale_detail', pk=sale.pk)

@login_required
@group_required('Sales')
@transaction.atomic
def sale_cancel(request, pk):
    """Cancel a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    
    # Check if sale has approved stock out - Use property
    if sale.status == 'COMPLETED' and sale.has_approved_stock_out:
        messages.error(request, 'Cannot cancel sale that has approved stock out.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    if request.method == 'POST':
        try:
            # If sale has pending stock out, delete it
            if sale.inventory_stock_out and sale.inventory_stock_out.status == 'pending':
                sale.inventory_stock_out.delete()
            
            # Update sale status
            sale.status = 'CANCELLED'
            sale.save(update_fields=['status', 'updated_at'])
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='UPDATE',
                module='SALES',
                object_type='Sale',
                object_id=sale.id,
                description=f'Cancelled sale #{sale.sale_number}',
                request=request
            )
            
            messages.success(request, f'Sale {sale.sale_number} cancelled successfully!')
            return redirect('sales:sale_detail', pk=sale.pk)
            
        except Exception as e:
            messages.error(request, f'Error cancelling sale: {str(e)}')
    
    return render(request, 'sales/sale_confirm_cancel.html', {'sale': sale})

@login_required
@group_required('Sales')
@transaction.atomic
def sale_add_payment(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, sale=sale)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.sale = sale
                    payment.currency = 'Tsh'
                    payment.received_by = request.user.get_full_name() or request.user.username
                    payment.full_clean()
                    payment.save()
                    
                    # ✅ ADD THIS: Update linked income record
                    if sale.income_records.exists():
                        for income in sale.income_records.all():
                            # Check if sale is fully paid
                            if sale.is_paid:
                                income.is_paid = True
                                income.payment_date = payment.payment_date
                                income.payment_method = payment.payment_method
                                income.save()
                    
                    audit_log(...)
                    messages.success(...)
                    return redirect('sales:sale_detail', pk=sale.pk)
                    
            except Exception as e:
                messages.error(request, f'Error recording payment: {str(e)}')
    else:
        initial_amount = min(sale.balance_due, sale.net_amount)
        form = PaymentForm(
            initial={
                'amount': initial_amount,
                'currency': 'Tsh',
                'payment_method': 'CASH',
                'payment_status': 'COMPLETED',
                'payment_date': timezone.now().date()
            },
            sale=sale
        )
    
    balance_due = float(sale.balance_due) if sale.balance_due > 0 else 0
    quick_amounts = {
        '25_percent': int(balance_due * 0.25),
        '50_percent': int(balance_due * 0.50),
        '75_percent': int(balance_due * 0.75),
        '100_percent': int(balance_due),
    } if balance_due > 0 else {}
    
    context = {
        'sale': sale,
        'form': form,
        'quick_amounts': quick_amounts,
    }
    
    return render(request, 'sales/payment_form.html', context)

@login_required
def sales_report(request):
    """Sales reports and analytics - Clean production version"""
    from datetime import datetime, timedelta
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get date filters from request
    if request.GET.get('start_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if request.GET.get('end_date'):
        try:
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Ensure start_date is before end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Get quick period if provided
    quick_period = request.GET.get('period', '')
    
    # Date range sales
    date_range_sales = Sale.objects.filter(
        status='COMPLETED',
        sale_date__gte=start_date,
        sale_date__lte=end_date
    ).select_related('customer')
    
    # Daily sales summary
    daily_summary = date_range_sales.values('sale_date').annotate(
        total_sales=Count('id'),
        total_amount=Sum('net_amount')
    ).annotate(
        avg_amount=Sum('net_amount') / Count('id')
    ).order_by('sale_date')
    
    # Product sales
    product_sales = SaleItem.objects.filter(
        sale__status='COMPLETED',
        sale__sale_date__gte=start_date,
        sale__sale_date__lte=end_date
    ).values(
        'item__name', 
        'item__sku'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('total_price')
    ).annotate(
        avg_price=Sum('total_price') / Sum('quantity')
    ).order_by('-total_amount')
    
    # Customer summary
    customer_summary = date_range_sales.values(
        'customer__name', 
        'customer__id'
    ).annotate(
        total_sales=Count('id'),
        total_amount=Sum('net_amount')
    ).order_by('-total_amount')
    
    # Summary statistics
    summary_stats = date_range_sales.aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('net_amount'),
        avg_sale_value=Avg('net_amount')
    )
    
    total_sales = summary_stats['total_sales'] or 0
    total_revenue = summary_stats['total_revenue'] or Decimal('0')
    avg_sale_value = summary_stats['avg_sale_value'] or Decimal('0')
    
    # Sales by type
    sales_by_type = date_range_sales.values('sale_type').annotate(
        count=Count('id'),
        amount=Sum('net_amount')
    ).order_by('-amount')
    
    # Stock out statistics
    stock_out_stats = Sale.objects.filter(
        inventory_stock_out__isnull=False,
        inventory_stock_out__status='approved',
        sale_date__gte=start_date,
        sale_date__lte=end_date
    ).count()
    
    # Prepare data for charts - FIX: Use safe JSON
    daily_data_for_chart = []
    for day in daily_summary:
        daily_data_for_chart.append({
            'sale_date': day['sale_date'].strftime('%Y-%m-%d'),
            'total_sales': int(day['total_sales']),
            'total_amount': float(day['total_amount'] or 0)
        })
    
    product_data_for_chart = []
    for product in product_sales[:10]:
        product_data_for_chart.append({
            'item__name': str(product['item__name'] or 'Unknown'),
            'total_amount': float(product['total_amount'] or 0)
        })
    
    sales_by_type_data = []
    for st in sales_by_type:
        sales_by_type_data.append({
            'sale_type': str(st['sale_type'] or 'Unknown'),
            'amount': float(st['amount'] or 0)
        })
    
    # IMPORTANT FIX: Use json.dumps to properly serialize
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'quick_period': quick_period,
        'daily_summary': daily_summary,
        'product_sales': product_sales,
        'customer_summary': customer_summary,
        'sales_by_type': sales_by_type,
        'stock_out_stats': stock_out_stats,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'avg_sale_value': avg_sale_value,
        'daily_data_json': json.dumps(daily_data_for_chart, cls=DecimalEncoder),
        'product_data_json': json.dumps(product_data_for_chart, cls=DecimalEncoder),
        'sales_by_type_json': json.dumps(sales_by_type_data, cls=DecimalEncoder),
    }
    
    return render(request, 'sales/report.html', context)

@login_required
@group_required('Sales')
def sale_delete(request, pk):
    """Delete sale (only if draft)"""
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status != 'DRAFT':
        messages.error(request, 'Can only delete draft sales.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    if request.method == 'POST':
        sale_number = sale.sale_number
        sale.delete()
        messages.success(request, f'Sale {sale_number} deleted successfully!')
        return redirect('sales:sale_list')
    
    return render(request, 'sales/sale_confirm_delete.html', {'sale': sale})

@login_required
@group_required('Sales')
def payment_list(request):
    """List all payments"""
    payments = Payment.objects.select_related('sale', 'sale__customer').order_by('-payment_date')
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    method_filter = request.GET.get('method')
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    
    sale_filter = request.GET.get('sale')
    if sale_filter:
        payments = payments.filter(sale__sale_number__icontains=sale_filter)
    
    # Total payments in Tsh
    total_payments = payments.filter(payment_status='COMPLETED').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    context = {
        'payments': payments,
        'payment_methods': Payment.PAYMENT_METHODS,
        'total_payments': total_payments,
    }
    return render(request, 'sales/payment_list.html', context)

@login_required
@group_required('Sales')
def check_stock_availability(request, pk):
    """Check stock availability for a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    
    is_available, message = sale.check_stock_availability()
    
    if is_available:
        messages.success(request, message)
    else:
        messages.warning(request, message)
    
    return redirect('sales:sale_detail', pk=sale.pk)

@login_required
@group_required('Sales')
def view_stock_out_status(request, pk):
    """View detailed stock out status for a sale"""
    sale = get_object_or_404(
        Sale.objects.select_related('inventory_stock_out'),
        pk=pk
    )
    
    stock_out = sale.inventory_stock_out
    
    if not stock_out:
        messages.info(request, 'No stock out request for this sale yet.')
        return redirect('sales:sale_detail', pk=sale.pk)
    
    context = {
        'sale': sale,
        'stock_out': stock_out,
    }
    return render(request, 'sales/stock_out_status.html', context)

@login_required
@group_required('Sales')
def pending_stock_outs(request):
    """View all sales with pending stock outs"""
    pending_sales = Sale.objects.filter(
        status='STOCK_OUT_PENDING'
    ).select_related('customer', 'inventory_stock_out').order_by('-stock_out_request_date')
    
    context = {
        'pending_sales': pending_sales,
        'title': 'Sales with Pending Stock Outs',
    }
    return render(request, 'sales/pending_stock_outs.html', context)

@login_required
@group_required('Sales')
def sale_items_report(request):
    """Report of all sale items"""
    start_date = timezone.now().date() - timedelta(days=30)
    end_date = timezone.now().date()
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    sale_items = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status='COMPLETED'
    ).select_related('sale', 'item').order_by('-created_at')
    
    # Summary
    total_items = sale_items.count()
    total_quantity = sale_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
    total_amount = sale_items.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    
    context = {
        'sale_items': sale_items,
        'start_date': start_date,
        'end_date': end_date,
        'total_items': total_items,
        'total_quantity': total_quantity,
        'total_amount': total_amount,
    }
    return render(request, 'sales/sale_items_report.html', context)

@login_required
@group_required('Sales')
def download_sales_pdf(request):
    """Download sales list as PDF with proper table"""
    sales = Sale.objects.select_related('customer').order_by('-created_at')
    
    # Apply same filters as sale_list
    status_filter = request.GET.get('status')
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    customer_filter = request.GET.get('customer')
    if customer_filter:
        sales = sales.filter(customer__id=customer_filter)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        sales = sales.filter(sale_date__gte=date_from)
    if date_to:
        sales = sales.filter(sale_date__lte=date_to)
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    
    # Create PDF document with landscape orientation
    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title = Paragraph("SALES REPORT", styles['Title'])
    elements.append(title)
    
    # Filter info
    filter_text = f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    if status_filter:
        filter_text += f" | Status: {status_filter}"
    if date_from and date_to:
        filter_text += f" | Date Range: {date_from} to {date_to}"
    
    subtitle = Paragraph(filter_text, styles['Normal'])
    elements.append(subtitle)
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Prepare table data with ALL fields
    data = []
    
    # Table headers with ALL columns
    headers = [
        'Sale #', 
        'Date', 
        'Customer', 
        'Sale Type',
        'Amount (Tsh)', 
        'Paid (Tsh)', 
        'Balance (Tsh)', 
        'Payment Status',
        'Sale Status',
        'Stock Out'
    ]
    data.append(headers)
    
    # Add sales data
    for sale in sales:
        # Determine payment status
        if sale.is_paid:
            payment_status = "Fully Paid"
        elif sale.amount_paid > 0:
            payment_status = "Partial"
        else:
            payment_status = "Unpaid"
        
        # Stock out status
        if sale.inventory_stock_out:
            if sale.inventory_stock_out.status == 'approved':
                stock_out = "Approved"
            elif sale.inventory_stock_out.status == 'pending':
                stock_out = "Pending"
            else:
                stock_out = sale.inventory_stock_out.status.title()
        else:
            stock_out = "Not Requested"
        
        row = [
            sale.sale_number,
            sale.sale_date.strftime('%Y-%m-%d') if sale.sale_date else '',
            sale.customer.name,
            sale.get_sale_type_display(),
            f"{sale.net_amount:,.0f}",
            f"{sale.amount_paid:,.0f}",
            f"{sale.balance_due:,.0f}",
            payment_status,
            sale.get_status_display(),
            stock_out
        ]
        data.append(row)
    
    # Create table with proper styling
    table = Table(data)
    
    # Style the table
    style = TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
        
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Number columns alignment
        ('ALIGN', (4, 1), (6, -1), 'RIGHT'),  # Amount columns
    ])
    
    table.setStyle(style)
    elements.append(table)
    
    # Add summary section
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Calculate totals
    total_sales = sales.count()
    total_amount = sum(sale.net_amount for sale in sales) if sales else Decimal('0')
    total_paid = sum(sale.amount_paid for sale in sales) if sales else Decimal('0')
    total_balance = sum(sale.balance_due for sale in sales) if sales else Decimal('0')
    
    summary_data = [
        ['Total Sales:', str(total_sales)],
        ['Total Amount (Tsh):', f"{total_amount:,.0f}"],
        ['Total Paid (Tsh):', f"{total_paid:,.0f}"],
        ['Total Balance Due (Tsh):', f"{total_balance:,.0f}"],
        ['Completed Sales:', str(sales.filter(status='COMPLETED').count())],
        ['Pending Payments:', str(sales.filter(is_paid=False, balance_due__gt=0).count())]
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 100])
    summary_style = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D9E1F2')),
    ])
    summary_table.setStyle(summary_style)
    elements.append(summary_table)
    
    # Build PDF
    doc.build(elements)
    
    return response