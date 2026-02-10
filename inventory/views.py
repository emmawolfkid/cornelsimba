# cornelsimba/inventory/views.py - FIXED VERSION
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from functools import wraps
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import Item, StockIn, StockOut, StockAdjustment, StockHistory
from .forms import ItemForm, StockInForm, StockOutForm, StockAdjustmentForm, ApproveRejectForm
from sales.models import Sale  # Add this import
from audit.utils import audit_log
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal

USD_TO_TSH = getattr(settings, 'USD_TO_TSH', 2500)

def tsh_converter(usd_amount):
    return usd_amount * USD_TO_TSH

def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('inventory:dashboard')  # Redirect to inventory dashboard
        return _wrapped_view
    return decorator


@login_required
@group_required('Inventory')
def inventory_dashboard(request):
    # Get unique active items
    unique_items = Item.objects.filter(is_active=True).order_by('name')
    total_items = unique_items.count()
    
    # Calculate total quantity
    total_quantity_result = Item.objects.filter(is_active=True).aggregate(total_qty=Sum('quantity'))
    total_quantity = total_quantity_result['total_qty'] or 0
    
    # Stock alerts
    low_stock_items = Item.objects.filter(
        quantity__lte=F('reorder_level'),
        quantity__gt=F('minimum_stock'),
        is_active=True
    )
    
    critical_stock_items = Item.objects.filter(
        quantity__lte=F('minimum_stock'),
        is_active=True
    )
    
    low_stock_combined = list(critical_stock_items) + list(low_stock_items)
    
    # Get pending sales stock outs count
    pending_stockouts_count = StockOut.objects.filter(
        status='pending',
        purpose='SALE'
    ).count()

    # Recent activities
    recent_stock_ins = StockIn.objects.select_related('item').order_by('-date')[:10]
    recent_stock_outs = StockOut.objects.select_related('item').order_by('-date')[:10]
    pending_adjustments = StockAdjustment.objects.filter(status='pending').count()
    
    # Monthly summary
    thirty_days_ago = datetime.now() - timedelta(days=30)
    stock_ins_month = StockIn.objects.filter(date__gte=thirty_days_ago).aggregate(
        total_quantity=Sum('quantity'),
    ) or {'total_quantity': 0}
    
    stock_outs_month = StockOut.objects.filter(date__gte=thirty_days_ago).aggregate(
        total_quantity=Sum('quantity'),
    ) or {'total_quantity': 0}
    
    context = {
        'total_items': total_items,
        'total_quantity': total_quantity,
        'low_stock_count': low_stock_items.count() + critical_stock_items.count(),
        'critical_stock_count': critical_stock_items.count(),
        'low_stock_items': low_stock_items,
        'critical_stock_items': critical_stock_items,
        'low_stock': low_stock_combined,
        'pending_stockouts_count': pending_stockouts_count,
        'recent_stock_ins': recent_stock_ins,
        'recent_stock_outs': recent_stock_outs,
        'pending_adjustments': pending_adjustments,
        'stock_ins_month': stock_ins_month,
        'stock_outs_month': stock_outs_month,
        'items': unique_items,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
@group_required('Inventory')
def item_list(request):
    items = Item.objects.filter(is_active=True).order_by('name')
    category_filter = request.GET.get('category')
    if category_filter:
        items = items.filter(category=category_filter)
    
    status_filter = request.GET.get('status')
    if status_filter == 'low':
        items = items.filter(quantity__lte=F('reorder_level'), quantity__gt=F('minimum_stock'))
    elif status_filter == 'critical':
        items = items.filter(quantity__lte=F('minimum_stock'))
    elif status_filter == 'out_of_stock':
        items = items.filter(quantity=0)
    
    # Add pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(items, 100)  # Show 100 items per page
    
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)
    
    # Calculate counts for current page items
    low_stock_count = 0
    critical_stock_count = 0
    inactive_items_count = 0
    
    for item in items_page:
        if not item.is_active:
            inactive_items_count += 1
        elif item.quantity <= item.minimum_stock:
            critical_stock_count += 1
        elif item.quantity <= item.reorder_level:
            low_stock_count += 1
    
    context = {
        'items': items_page,  # Changed from items to items_page
        'low_stock_count': low_stock_count,
        'critical_stock_count': critical_stock_count,
        'inactive_items_count': inactive_items_count,
        'category_choices': Item.CATEGORY_CHOICES,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/item_list.html', context)

@login_required
@group_required('Inventory')
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk, is_active=True)

    
    stock_ins = item.stock_ins.all().order_by('-date')[:20]
    stock_outs = item.stock_outs.all().order_by('-date')[:20]
    adjustments = item.stock_adjustments.all().order_by('-created_at')[:20]
    
    total_in = item.stock_ins.aggregate(total=Sum('quantity'))['total'] or 0
    total_out = item.stock_outs.aggregate(total=Sum('quantity'))['total'] or 0
    total_adjustment = item.stock_adjustments.filter(status='approved').aggregate(
        total=Sum('adjustment_quantity')
    )['total'] or 0
    
    stock_history = item.stock_history.all().order_by('-created_at')[:50]
    
    context = {
        'item': item,
        'stock_ins': stock_ins,
        'stock_outs': stock_outs,
        'adjustments': adjustments,
        'stock_history': stock_history,
        'total_in': total_in,
        'total_out': total_out,
        'total_adjustment': total_adjustment,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/item_detail.html', context)


@login_required
@group_required('Inventory')
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='INVENTORY',
                object_type='Item',
                object_id=item.id,
                description=f'Created inventory item: "{item.name}" (SKU: {item.sku})',
                request=request
            )
            
            messages.success(request, f'Item "{item.name}" created successfully!')
            return redirect('inventory:item_detail', pk=item.pk)
    else:
        form = ItemForm()
    
    return render(request, 'inventory/item_form.html', {'form': form})


@login_required
@group_required('Inventory')
def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            old_name = item.name  # Save old name
            old_qty = item.quantity  # Save old quantity
            
            form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='UPDATE',
                module='INVENTORY',
                object_type='Item',
                object_id=item.id,
                description=f'Updated inventory item: "{old_name}" → "{item.name}" (Qty: {old_qty} → {item.quantity})',
                request=request
            )
            
            messages.success(request, f'Item "{item.name}" updated successfully!')
            return redirect('inventory:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'inventory/item_form.html', {'form': form, 'item': item})


# REMOVED: item_delete function - Inventory users should NOT delete items


@login_required
@group_required('Inventory')
def stock_in_detail(request, pk):
    stock_in = get_object_or_404(StockIn, pk=pk)
    return render(request, 'inventory/stock_in_detail.html', {'stock_in': stock_in})


@login_required
@group_required('Inventory')
def stock_in_list(request):
    stock_ins = StockIn.objects.select_related('item').order_by('-date')
    
    source_filter = request.GET.get('source')
    if source_filter:
        stock_ins = stock_ins.filter(source=source_filter)
    
    status_filter = request.GET.get('status')
    if status_filter:
        stock_ins = stock_ins.filter(status=status_filter)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        stock_ins = stock_ins.filter(date__date__gte=date_from)
    if date_to:
        stock_ins = stock_ins.filter(date__date__lte=date_to)
    
    # Add pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(stock_ins, 50)  # Show 50 items per page
    
    try:
        stock_ins_page = paginator.page(page)
    except PageNotAnInteger:
        stock_ins_page = paginator.page(1)
    except EmptyPage:
        stock_ins_page = paginator.page(paginator.num_pages)
    
    context = {
        'stock_ins': stock_ins_page,  # Changed from stock_ins to stock_ins_page
        'source_choices': StockIn.SOURCE_CHOICES,
        'status_choices': StockIn.STATUS_CHOICES,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/stock_in_list.html', context)

@login_required
@group_required('Inventory')
def stock_in_create(request):
    if request.method == 'POST':
        form = StockInForm(request.POST, user=request.user)
        if form.is_valid():
            stock_in = form.save()
            
            # Create stock history
            StockHistory.objects.create(
                item=stock_in.item,
                transaction_type='STOCK_IN',
                quantity=stock_in.quantity,
                previous_quantity=stock_in.item.quantity - stock_in.quantity,
                new_quantity=stock_in.item.quantity,
                reference_id=stock_in.id,
                reference_model='StockIn',
                reference=stock_in.reference,
                notes=stock_in.notes,
                created_by=request.user.get_full_name() or request.user.username
            )
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='INVENTORY',
                object_type='StockIn',
                object_id=stock_in.id,
                description=f'Stock In: Added {stock_in.quantity} {stock_in.item.unit_of_measure} of "{stock_in.item.name}"',
                request=request
            )
            
            messages.success(request, f'Stock In recorded for {stock_in.item.name}!')
            return redirect('inventory:stock_in_list')
    else:
        form = StockInForm(user=request.user)
    
    return render(request, 'inventory/stock_in_form.html', {'form': form})

@login_required
def stock_in_edit(request, pk):
    stock_in = get_object_or_404(StockIn, pk=pk)
    
    # Check if user can edit (only pending or within 1 hour of creation)
    can_edit = False
    if stock_in.status == 'pending':
        can_edit = True
    elif stock_in.created_at and (timezone.now() - stock_in.created_at).total_seconds() < 3600:  # 1 hour
        can_edit = True
    
    if not can_edit and not request.user.groups.filter(name='Manager').exists():
        messages.error(request, 'This stock entry cannot be edited. Please create a stock adjustment instead.')
        return redirect('inventory:stock_in_list')
    
    if request.method == 'POST':
        form = StockInForm(request.POST, instance=stock_in, user=request.user)
        if form.is_valid():
            stock_in = form.save()
            messages.success(request, f'Stock In updated for {stock_in.item.name}!')
            return redirect('inventory:stock_in_list')
    else:
        form = StockInForm(instance=stock_in, user=request.user)
    
    return render(request, 'inventory/stock_in_form.html', {
        'form': form,
        'editing': True,
        'stock_in': stock_in
    })


@login_required
@group_required('Inventory')
def stock_out_list(request):
    stock_outs = StockOut.objects.select_related('item').order_by('-date')
    
    purpose_filter = request.GET.get('purpose')
    if purpose_filter:
        stock_outs = stock_outs.filter(purpose=purpose_filter)
    
    status_filter = request.GET.get('status')
    if status_filter:
        stock_outs = stock_outs.filter(status=status_filter)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        stock_outs = stock_outs.filter(date__date__gte=date_from)
    if date_to:
        stock_outs = stock_outs.filter(date__date__lte=date_to)
    
    # Add pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(stock_outs, 50)  # Show 50 items per page
    
    try:
        stock_outs_page = paginator.page(page)
    except PageNotAnInteger:
        stock_outs_page = paginator.page(1)
    except EmptyPage:
        stock_outs_page = paginator.page(paginator.num_pages)
    
    context = {
        'stock_outs': stock_outs_page,  # Changed from stock_outs to stock_outs_page
        'purpose_choices': StockOut.PURPOSE_CHOICES,
        'status_choices': StockOut.STATUS_CHOICES,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/stock_out_list.html', context)


@login_required
@group_required('Inventory')
@transaction.atomic
def stock_out_create(request):
    if request.method == 'POST':
        form = StockOutForm(request.POST, user=request.user)
        if form.is_valid():
            stock_out = form.save()
            
            # Create stock history
            StockHistory.objects.create(
                item=stock_out.item,
                transaction_type='STOCK_OUT',
                quantity=stock_out.quantity,
                previous_quantity=stock_out.item.quantity + stock_out.quantity,
                new_quantity=stock_out.item.quantity,
                reference_id=stock_out.id,
                reference_model='StockOut',
                reference=stock_out.reference,
                notes=stock_out.notes,
                created_by=request.user.get_full_name() or request.user.username
            )
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='INVENTORY',
                object_type='StockOut',
                object_id=stock_out.id,
                description=f'Stock Out: Requested {stock_out.quantity} {stock_out.item.unit_of_measure} of "{stock_out.item.name}"',
                request=request
            )
            
            messages.success(request, f'Stock Out recorded for {stock_out.item.name}!')
            return redirect('inventory:stock_out_list')
    else:
        form = StockOutForm(user=request.user)
    
    items = Item.objects.filter(is_active=True, quantity__gt=0).order_by('name')
    return render(request, 'inventory/stock_out_form.html', {
        'form': form,
        'items': items,
        'usd_to_tsh': USD_TO_TSH,
    })


@login_required
@group_required('Inventory')
def stock_adjustment_list(request):
    adjustments = StockAdjustment.objects.select_related('item').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        adjustments = adjustments.filter(status=status_filter)
    
    type_filter = request.GET.get('type')
    if type_filter:
        adjustments = adjustments.filter(adjustment_type=type_filter)
    
    # Add pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(adjustments, 50)  # Show 50 items per page
    
    try:
        adjustments_page = paginator.page(page)
    except PageNotAnInteger:
        adjustments_page = paginator.page(1)
    except EmptyPage:
        adjustments_page = paginator.page(paginator.num_pages)
    
    context = {
        'adjustments': adjustments_page,  # Changed from adjustments to adjustments_page
        'status_choices': StockAdjustment._meta.get_field('status').choices,
        'type_choices': StockAdjustment.ADJUSTMENT_TYPE_CHOICES,
    }
    return render(request, 'inventory/adjustment_list.html', context)


@login_required
@group_required('Inventory')
def stock_adjustment_create(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST, user=request.user)
        if form.is_valid():
            adjustment = form.save()
            
            # Create stock history for pending adjustment
            StockHistory.objects.create(
                item=adjustment.item,
                transaction_type='ADJUSTMENT',
                quantity=adjustment.adjustment_quantity,
                previous_quantity=adjustment.item.quantity,
                new_quantity=adjustment.item.quantity,  # Won't change until approved
                reference_id=adjustment.id,
                reference_model='StockAdjustment',
                reference=f"Adjustment Request: {adjustment.get_adjustment_type_display()}",
                notes=adjustment.reason,
                created_by=request.user.get_full_name() or request.user.username
            )
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='INVENTORY',
                object_type='StockAdjustment',
                object_id=adjustment.id,
                description=f'Stock adjustment requested: {adjustment.adjustment_quantity} {adjustment.item.unit_of_measure} of "{adjustment.item.name}"',
                request=request
            )
            
            messages.success(request, 
                f'Adjustment request submitted for {adjustment.item.name}! '
                f'Quantity: {adjustment.adjustment_quantity}. Awaiting manager approval.'
            )
            return redirect('inventory:adjustment_list')
    else:
        form = StockAdjustmentForm(user=request.user)
    
    return render(request, 'inventory/adjustment_form.html', {'form': form})


@login_required
@group_required('Manager')
def stock_adjustment_approve(request, pk):
    adjustment = get_object_or_404(StockAdjustment, pk=pk)
    
    if request.method == 'POST':
        form = ApproveRejectForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'approve':
                adjustment.status = 'approved'
                adjustment.approved_by = request.user
                adjustment.approved_at = timezone.now()
                adjustment.rejected_by = None
                adjustment.rejected_at = None
                adjustment.rejection_reason = None
                
                # Update stock
                old_quantity = adjustment.item.quantity
                adjustment.item.quantity += adjustment.adjustment_quantity
                adjustment.item.save()
                
                # Update stock history
                StockHistory.objects.create(
                    item=adjustment.item,
                    transaction_type='ADJUSTMENT',
                    quantity=adjustment.adjustment_quantity,
                    previous_quantity=old_quantity,
                    new_quantity=adjustment.item.quantity,
                    reference_id=adjustment.id,
                    reference_model='StockAdjustment',
                    reference=f"Approved Adjustment: {adjustment.get_adjustment_type_display()}",
                    notes=adjustment.reason,
                    created_by=request.user.get_full_name() or request.user.username
                )
                
                adjustment.save()
                
                # 🔴 AUDIT ADD - After this line
                audit_log(
                    user=request.user,
                    action='APPROVE',
                    module='INVENTORY',
                    object_type='StockAdjustment',
                    object_id=adjustment.id,
                    description=f'Approved stock adjustment: {adjustment.adjustment_quantity} {adjustment.item.unit_of_measure} of "{adjustment.item.name}" (Qty: {old_quantity} → {adjustment.item.quantity})',
                    request=request
                )
                
                messages.success(request, f'Adjustment approved for {adjustment.item.name}!')
                
            elif action == 'reject':
                adjustment.status = 'rejected'
                adjustment.rejected_by = request.user
                adjustment.rejected_at = timezone.now()
                adjustment.rejection_reason = form.cleaned_data['rejection_reason']
                adjustment.save()
                
                # 🔴 AUDIT ADD - After this line
                audit_log(
                    user=request.user,
                    action='REJECT',
                    module='INVENTORY',
                    object_type='StockAdjustment',
                    object_id=adjustment.id,
                    description=f'Rejected stock adjustment: {adjustment.adjustment_quantity} {adjustment.item.unit_of_measure} of "{adjustment.item.name}". Reason: {adjustment.rejection_reason}',
                    request=request
                )
                
                messages.warning(request, f'Adjustment rejected for {adjustment.item.name}.')
            
            return redirect('inventory:adjustment_list')
    else:
        form = ApproveRejectForm()
    
    return render(request, 'inventory/adjustment_approve.html', {
        'form': form,
        'adjustment': adjustment
    })


@login_required
@group_required('Inventory')
def stock_report(request):
    items = Item.objects.filter(is_active=True).order_by('category', 'name')
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    daily_summary = StockHistory.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'day': 'DATE(created_at)'}
    ).values('day', 'transaction_type').annotate(
        total_quantity=Sum('quantity'),
        count=Count('id')
    ).order_by('-day')
    
    total_items = items.count()
    items_low_stock = items.filter(
        quantity__lte=F('reorder_level'),
        quantity__gt=F('minimum_stock')
    ).count()
    items_critical = items.filter(quantity__lte=F('minimum_stock')).count()
    
    category_summary = {}
    for item in items:
        category = item.get_category_display()
        if category not in category_summary:
            category_summary[category] = {
                'count': 0,
                'total_quantity': 0,
                'items': []
            }
        category_summary[category]['count'] += 1
        category_summary[category]['total_quantity'] += item.quantity

        category_summary[category]['items'].append(item)
    
    recent_history = StockHistory.objects.select_related('item').all().order_by('-created_at')[:100]
    
    context = {
        'items': items,
        'total_items': total_items,
        'items_low_stock': items_low_stock,
        'items_critical': items_critical,
        'category_summary': category_summary,
        'daily_summary': daily_summary,
        'recent_history': recent_history,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/stock_report.html', context)


@login_required
@group_required('Inventory')
def procurement_stock(request):
    procurement_stock = StockIn.objects.filter(
        source='Purchase'
    ).select_related('item').order_by('-date')
    
    supplier_summary = {}
    for stock_in in procurement_stock:
        supplier = stock_in.supplier or 'Unknown'
        if supplier not in supplier_summary:
            supplier_summary[supplier] = {
                'count': 0,
                'total_quantity': 0,
                'items': set()
            }
        supplier_summary[supplier]['count'] += 1
        supplier_summary[supplier]['total_quantity'] += stock_in.quantity

        supplier_summary[supplier]['items'].add(stock_in.item.name)
    
    context = {
        'procurement_stock': procurement_stock,
        'supplier_summary': supplier_summary,
        'usd_to_tsh': USD_TO_TSH,

    }
    return render(request, 'inventory/procurement_stock.html', context)


@login_required
def adjustment_detail(request, pk):
    adjustment = get_object_or_404(StockAdjustment, pk=pk)
    return render(request, 'inventory/adjustment_detail.html', {'adjustment': adjustment})

@login_required
@group_required('Inventory')
@transaction.atomic
def approve_stockout(request, pk):
    """Approve a pending stock out request - FIXED VERSION"""
    stock_out = get_object_or_404(StockOut, pk=pk)
    
    # Check if already approved
    if stock_out.status == 'approved':
        messages.warning(request, 'This stock out is already approved.')
        return redirect('inventory:stock_out_list')
    
    # Check if stock is available
    if stock_out.item.quantity < stock_out.quantity:
        messages.error(request, 
            f'Insufficient stock for {stock_out.item.name}. '
            f'Available: {stock_out.item.quantity} {stock_out.item.unit_of_measure}, '
            f'Required: {stock_out.quantity} {stock_out.item.unit_of_measure}')
        return redirect('inventory:stock_out_list')
    
    try:
        # Update stock out status
        stock_out.status = 'approved'
        stock_out.approved_by = request.user
        stock_out.approved_at = timezone.now()
        stock_out.save()
        
        # Update item quantity (FIXED – NO FLOAT DRIFT)
        stock_out.item.quantity = (stock_out.item.quantity - stock_out.quantity).quantize(Decimal('0.001'))
        stock_out.item.save(update_fields=['quantity'])
        
        # Create stock history
        StockHistory.objects.create(
            item=stock_out.item,
            transaction_type='STOCK_OUT',
            quantity=stock_out.quantity,
            previous_quantity=stock_out.item.quantity + stock_out.quantity,
            new_quantity=stock_out.item.quantity,
            reference_id=stock_out.id,
            reference_model='StockOut',
            reference=stock_out.reference,
            notes=f"Approved stock out: {stock_out.notes or ''}",
            created_by=request.user.get_full_name() or request.user.username
        )
        
        # 🔴 CRITICAL FIX: Update the linked sale status
        if stock_out.linked_sale:
            sale = stock_out.linked_sale
            
            # Update sale status to COMPLETED
            sale.status = 'COMPLETED'
            sale.stock_out_processed_date = timezone.now()
            sale.save(update_fields=['status', 'stock_out_processed_date', 'updated_at'])
            
            # Update all sale items to mark as stocked out
            for sale_item in sale.items.all():
                sale_item.is_stocked_out = True
                sale_item.stock_out_date = timezone.now()
                sale_item.save(update_fields=['is_stocked_out', 'stock_out_date'])
            
            # ✅ AUDIT: Sale status update
            audit_log(
                user=request.user,
                action='UPDATE',
                module='SALES',
                object_type='Sale',
                object_id=sale.id,
                description=f'Inventory approved stock out, marking sale #{sale.sale_number} as COMPLETED',
                request=request
            )
            
        # ✅ FINANCE INTEGRATION: Create income record if not exists
        if stock_out.purpose == 'SALE' and stock_out.linked_sale:
            from finance.models import Income
            
            sale = stock_out.linked_sale
            
            # Check if income record already exists
            if not Income.objects.filter(sale=sale).exists():
                try:
                    income = Income.create_from_sale(sale, request.user)
                    
                    # ✅ AUDIT: Income creation
                    audit_log(
                        user=request.user,
                        action='CREATE',
                        module='FINANCE',
                        object_type='Income',
                        object_id=income.id,
                        description=f'Auto-created income from approved stock out: Tsh {income.amount:,.2f}',
                        request=request
                    )
                    
                    messages.success(request, 
                        f'✅ Stock out approved and income record created (Tsh {income.amount:,.2f}). '
                        f'Sale {sale.sale_number} marked as COMPLETED.'
                    )
                except Exception as e:
                    messages.error(request, 
                        f'⚠️ Stock out approved but failed to create income record: {str(e)}'
                    )
            else:
                messages.warning(request, 
                    f'ℹ️ Stock out approved but income record already exists for sale {sale.sale_number}.'
                )
        else:
            messages.success(request, 
                f'✅ Stock out approved for {stock_out.item.name}. '
                f'{stock_out.quantity} {stock_out.item.unit_of_measure} deducted from stock.'
            )
        
        # 🔴 AUDIT: Stock out approval
        audit_log(
            user=request.user,
            action='APPROVE',
            module='INVENTORY',
            object_type='StockOut',
            object_id=stock_out.id,
            description=f'Approved stock out: {stock_out.quantity} {stock_out.item.unit_of_measure} of "{stock_out.item.name}"',
            request=request
        )
        
    except Exception as e:
        messages.error(request, f'Error approving stock out: {str(e)}')
        # Rollback transaction if needed
        raise
    
    return redirect('inventory:stock_out_list')

@login_required
@group_required('Inventory')
def reject_stockout(request, pk):
    """Reject a pending stock out request - FIXED VERSION"""
    stock_out = get_object_or_404(StockOut, pk=pk)
    
    # Check if already processed
    if stock_out.status != 'pending':
        messages.warning(request, f'This stock out is already {stock_out.status}.')
        return redirect('inventory:stock_out_list')
    
    try:
        # Update stock out status
        stock_out.status = 'rejected'
        stock_out.rejected_by = request.user
        stock_out.rejected_at = timezone.now()
        stock_out.save()
        
        # 🔴 CRITICAL FIX: Update the linked sale status back to APPROVED
        if stock_out.linked_sale:
            sale = stock_out.linked_sale
            sale.status = 'APPROVED'  # Back to approved so sales can request again
            sale.inventory_stock_out = None
            sale.is_stock_out_requested = False
            sale.save(update_fields=['status', 'inventory_stock_out', 'is_stock_out_requested', 'updated_at'])
            
            # ✅ AUDIT: Sale status reverted
            audit_log(
                user=request.user,
                action='UPDATE',
                module='SALES',
                object_type='Sale',
                object_id=sale.id,
                description=f'Inventory rejected stock out, reverting sale #{sale.sale_number} to APPROVED status',
                request=request
            )
        
        # Create stock history for rejection
        StockHistory.objects.create(
            item=stock_out.item,
            transaction_type='STOCK_OUT',
            quantity=stock_out.quantity,
            previous_quantity=stock_out.item.quantity,
            new_quantity=stock_out.item.quantity,
            reference_id=stock_out.id,
            reference_model='StockOut',
            reference=stock_out.reference,
            notes=f"Rejected stock out: {stock_out.notes or ''}",
            created_by=request.user.get_full_name() or request.user.username
        )
        
        # 🔴 AUDIT: Stock out rejection
        audit_log(
            user=request.user,
            action='REJECT',
            module='INVENTORY',
            object_type='StockOut',
            object_id=stock_out.id,
            description=f'Rejected stock out: {stock_out.quantity} {stock_out.item.unit_of_measure} of "{stock_out.item.name}"',
            request=request
        )
        
        messages.warning(request, f'Stock out rejected for {stock_out.item.name}.')
        
    except Exception as e:
        messages.error(request, f'Error rejecting stock out: {str(e)}')
    
    return redirect('inventory:stock_out_list')


@login_required
@group_required('Inventory')
def pending_sales_stockouts(request):
    """Show sales that need stock out processing"""
    
    # Handle POST actions (approve/reject)
    if request.method == 'POST':
        stockout_id = request.POST.get('stockout_id')
        action = request.POST.get('action')
        
        if stockout_id and action:
            try:
                stockout = StockOut.objects.get(id=stockout_id, status='pending')
                
                if action == 'approve':
                    return redirect('inventory:approve_stockout', pk=stockout_id)
                elif action == 'reject':
                    return redirect('inventory:reject_stockout', pk=stockout_id)
                    
            except StockOut.DoesNotExist:
                messages.error(request, 'Stock out request not found.')
    
    # Get stock outs that are pending and sale-related
    pending_stockouts = StockOut.objects.filter(
        status='pending',
        purpose='SALE'
    ).select_related('item', 'linked_sale', 'linked_sale__customer').order_by('-date')
    
    # Calculate insufficient stock count
    insufficient_count = 0
    for stockout in pending_stockouts:
        if stockout.item.quantity < stockout.quantity:
            insufficient_count += 1
    
    # Count for dashboard display
    pending_count = pending_stockouts.count()
    
    # Get sales that are approved but don't have stock outs yet
    sales_without_stockout = Sale.objects.filter(
        status='APPROVED',
        inventory_stock_out__isnull=True
    ).select_related('customer')[:10]
    
    context = {
        'pending_stockouts': pending_stockouts,
        'pending_sales_stockouts': pending_count,
        'insufficient_count': insufficient_count,  # Add this
        'sales_without_stockout': sales_without_stockout,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/pending_sales_stockouts.html', context)

@login_required
@group_required('Inventory')
def stock_out_detail(request, pk):
    """View stock out details"""
    stock_out = get_object_or_404(
        StockOut.objects.select_related('item', 'linked_sale', 'linked_sale__customer'),
        pk=pk
    )
    
    context = {
        'stock_out': stock_out,
        'usd_to_tsh': USD_TO_TSH,
    }
    return render(request, 'inventory/stock_out_detail.html', context)


@login_required
@group_required('Inventory')
def stock_out_edit(request, pk):
    """Edit stock out (only if pending)"""
    stock_out = get_object_or_404(StockOut, pk=pk)
    
    if stock_out.status != 'pending':
        messages.error(request, 'Can only edit pending stock outs.')
        return redirect('inventory:stock_out_detail', pk=stock_out.pk)
    
    if request.method == 'POST':
        # Simplified - just update notes if needed
        stock_out.notes = request.POST.get('notes', stock_out.notes)
        stock_out.save()
        messages.success(request, 'Stock out updated successfully!')
        return redirect('inventory:stock_out_detail', pk=stock_out.pk)
    
    return redirect('inventory:stock_out_detail', pk=stock_out.pk)

@login_required
def get_item_details(request, pk):
    """API endpoint to get item details for stock in form"""
    try:
        item = Item.objects.get(pk=pk, is_active=True)
        data = {
            'success': True,
            'name': item.name,
            'quantity': float(item.quantity),
            'unit_of_measure': item.unit_of_measure,
            'reorder_level': float(item.reorder_level),
            'minimum_stock': float(item.minimum_stock),
        }
        return JsonResponse(data)
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})