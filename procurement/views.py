from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from functools import wraps
from datetime import datetime
from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from .forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet
from hr.models import Employee
from inventory.models import StockIn, Item
from audit.utils import audit_log
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

# Helper function to restrict access by group
def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('no_access')
        return _wrapped_view
    return decorator


@login_required
@group_required('Procurement')
def procurement_dashboard(request):
    # Get statistics
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_pos = PurchaseOrder.objects.count()
    pending_pos = PurchaseOrder.objects.filter(status='Pending').count()
    
    # Get recent purchase orders with user data
    recent_pos = PurchaseOrder.objects.select_related(
        'supplier', 
        'requested_by',
        'requested_by__user'  # Add this to get the user object
    ).order_by('-order_date')[:10]
    
    context = {
        'total_suppliers': total_suppliers,
        'total_pos': total_pos,
        'pending_pos': pending_pos,
        'recent_pos': recent_pos,
    }
    return render(request, 'procurement/dashboard.html', context)


@login_required
@group_required('Procurement')
def supplier_list(request):
    suppliers_list = Supplier.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(suppliers_list, 10)  # Show 10 suppliers per page
    page = request.GET.get('page')
    
    try:
        suppliers = paginator.page(page)
    except PageNotAnInteger:
        suppliers = paginator.page(1)
    except EmptyPage:
        suppliers = paginator.page(paginator.num_pages)
    
    return render(request, 'procurement/supplier_list.html', {'suppliers': suppliers})


@login_required
@group_required('Procurement')
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Get purchase orders with pagination
    purchase_orders_list = PurchaseOrder.objects.filter(
        supplier=supplier
    ).order_by('-order_date')
    
    paginator = Paginator(purchase_orders_list, 5)  # 5 per page
    page = request.GET.get('page')
    
    try:
        purchase_orders = paginator.page(page)
    except PageNotAnInteger:
        purchase_orders = paginator.page(1)
    except EmptyPage:
        purchase_orders = paginator.page(paginator.num_pages)
    
    context = {
        'supplier': supplier,
        'purchase_orders': purchase_orders,
    }
    return render(request, 'procurement/supplier_detail.html', context)


@login_required
@group_required('Procurement')
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='PROCUREMENT',
                object_type='Supplier',
                object_id=supplier.id,
                description=f'Created supplier: "{supplier.name}"',
                request=request
            )
            
            messages.success(request, f'Supplier {supplier.name} created successfully!')
            return redirect('procurement:supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'procurement/supplier_form.html', {'form': form})


@login_required
@group_required('Procurement')
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            old_name = supplier.name  # Save old name
            form.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='UPDATE',
                module='PROCUREMENT',
                object_type='Supplier',
                object_id=supplier.id,
                description=f'Updated supplier: "{old_name}" → "{supplier.name}"',
                request=request
            )
            
            messages.success(request, f'Supplier {supplier.name} updated successfully!')
            return redirect('procurement:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'procurement/supplier_form.html', {'form': form, 'supplier': supplier})

@login_required
@group_required('Procurement')
def purchase_order_list(request):
    purchase_orders_list = PurchaseOrder.objects.select_related(
        'supplier', 'requested_by', 'approved_by'
    ).order_by('-order_date')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        purchase_orders_list = purchase_orders_list.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        purchase_orders_list = purchase_orders_list.filter(
            Q(po_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query)
        )
    
    # Calculate stats
    total_value = sum(po.total_amount for po in purchase_orders_list)
    approved_count = purchase_orders_list.filter(status='Approved').count()
    pending_count = purchase_orders_list.filter(status='Pending').count()
    
    # Pagination
    paginator = Paginator(purchase_orders_list, 20)
    page = request.GET.get('page')
    
    try:
        purchase_orders = paginator.page(page)
    except PageNotAnInteger:
        purchase_orders = paginator.page(1)
    except EmptyPage:
        purchase_orders = paginator.page(paginator.num_pages)
    
    return render(request, 'procurement/purchase_order_list.html', {
        'purchase_orders': purchase_orders,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'total_value': total_value,
        'approved_count': approved_count,
        'pending_count': pending_count,
    })

@login_required
@group_required('Procurement')
def purchase_order_detail(request, pk):
    purchase_order = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier', 'requested_by', 'approved_by'),
        pk=pk
    )
    
    return render(request, 'procurement/purchase_order_detail.html', {
        'purchase_order': purchase_order,
    })


@login_required
@group_required('Procurement')
@transaction.atomic
def purchase_order_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            purchase_order = form.save(commit=False)
            purchase_order.status = 'Draft'
            
            # Auto-set requested_by if not provided but user has employee record
            if not purchase_order.requested_by:
                try:
                    employee = Employee.objects.get(user=request.user)
                    purchase_order.requested_by = employee
                    purchase_order.department = employee.department
                except Employee.DoesNotExist:
                    pass
            
            purchase_order.save()
            
            # Save formset
            items = formset.save(commit=False)
            for item in items:
                item.purchase_order = purchase_order
                item.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='CREATE',
                module='PROCUREMENT',
                object_type='PurchaseOrder',
                object_id=purchase_order.id,
                description=f'Created Purchase Order: {purchase_order.po_number} (Amount: Tsh {purchase_order.total_amount:,.2f})',
                request=request
            )
            
            messages.success(request, f'Purchase Order {purchase_order.po_number} created successfully!')
            return redirect('procurement:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()
    
    return render(request, 'procurement/purchase_order_form.html', {
        'form': form,
        'formset': formset,
    })


@login_required
@group_required('Procurement')
@transaction.atomic
def purchase_order_update(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Prevent editing delivered or cancelled orders
    if purchase_order.status in ['Delivered', 'Cancelled']:
        messages.error(request, 'Cannot edit a delivered or cancelled purchase order.')
        return redirect('procurement:purchase_order_detail', pk=pk)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        formset = PurchaseOrderItemFormSet(request.POST, instance=purchase_order)
        
        if form.is_valid() and formset.is_valid():
            purchase_order = form.save()
            formset.save()
            
            # 🔴 AUDIT ADD - After this line
            audit_log(
                user=request.user,
                action='UPDATE',
                module='PROCUREMENT',
                object_type='PurchaseOrder',
                object_id=purchase_order.id,
                description=f'Updated Purchase Order: {purchase_order.po_number}',
                request=request
            )
            
            messages.success(request, f'Purchase Order {purchase_order.po_number} updated successfully!')
            return redirect('procurement:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm(instance=purchase_order)
        formset = PurchaseOrderItemFormSet(instance=purchase_order)
    
    return render(request, 'procurement/purchase_order_form.html', {
        'form': form,
        'formset': formset,
        'purchase_order': purchase_order,
        'editing': True,
    })


@login_required
@group_required('Procurement')
def purchase_order_approve(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status != 'Pending':
        messages.error(request, 'Only pending orders can be approved.')
        return redirect('procurement:purchase_order_detail', pk=pk)
    
    # Get current user's employee record
    try:
        employee = Employee.objects.get(user=request.user)
        purchase_order.approved_by = employee
        purchase_order.status = 'Approved'
        purchase_order.save()
        
        # 🔴 AUDIT ADD - After this line
        audit_log(
            user=request.user,
            action='APPROVE',
            module='PROCUREMENT',
            object_type='PurchaseOrder',
            object_id=purchase_order.id,
            description=f'Approved Purchase Order: {purchase_order.po_number} (Amount: Tsh {purchase_order.total_amount:,.2f})',
            request=request
        )
        
        messages.success(request, f'Purchase Order {purchase_order.po_number} approved!')
    except Employee.DoesNotExist:
        messages.error(request, 'You need an employee record to approve purchase orders.')
    
    return redirect('procurement:purchase_order_detail', pk=pk)


@login_required
@group_required('Procurement')
@transaction.atomic
def mark_delivered(request, order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=order_id)
    
    if purchase_order.status != 'Approved':
        messages.error(request, 'Only approved orders can be marked as delivered.')
        return redirect('procurement:dashboard')
    
    # FIXED: Create stock entries for each item WITH PROPER LINK
    for item in purchase_order.items.all():
        StockIn.objects.create(
            item=item.item,
            quantity=item.quantity,
            supplier=purchase_order.supplier.name,
            reference=f"PO-{purchase_order.po_number}",
            purchase_order=purchase_order,  # FIXED: Link to PO
            source='Purchase',
            status='approved',
            received_by=request.user.get_full_name() or request.user.username
        )
    
    purchase_order.status = 'Delivered'
    purchase_order.save()
    
    # 🔴 AUDIT ADD - After this line
    audit_log(
        user=request.user,
        action='UPDATE',
        module='PROCUREMENT',
        object_type='PurchaseOrder',
        object_id=purchase_order.id,
        description=f'Marked Purchase Order as Delivered: {purchase_order.po_number} (Stock added to inventory)',
        request=request
    )
    
    # 🔴 AUDIT ADD - For each stock in created
    for item in purchase_order.items.all():
        audit_log(
            user=request.user,
            action='CREATE',
            module='INVENTORY',
            object_type='StockIn',
            object_id=item.id,
            description=f'Stock In from PO {purchase_order.po_number}: {item.quantity} {item.item.unit_of_measure} of "{item.item.name}"',
            request=request
        )
    
    messages.success(request, f'Purchase Order {purchase_order.po_number} marked as delivered and stock updated!')
    return redirect('procurement:dashboard')


@login_required
@group_required('Procurement')
def purchase_order_cancel(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status in ['Delivered', 'Cancelled']:
        messages.error(request, 'Cannot cancel a delivered or already cancelled order.')
        return redirect('procurement:purchase_order_detail', pk=pk)
    
    purchase_order.status = 'Cancelled'
    purchase_order.save()
    
    # 🔴 AUDIT ADD - After this line
    audit_log(
        user=request.user,
        action='UPDATE',
        module='PROCUREMENT',
        object_type='PurchaseOrder',
        object_id=purchase_order.id,
        description=f'Cancelled Purchase Order: {purchase_order.po_number}',
        request=request
    )
    
    messages.success(request, f'Purchase Order {purchase_order.po_number} cancelled!')
    return redirect('procurement:purchase_order_detail', pk=pk)


# Finance views (accessible only by Finance group)
@login_required
@group_required('Finance')
def finance_purchase_orders(request):
    """View for Finance to see all delivered POs ready for payment"""
    delivered_pos = PurchaseOrder.objects.filter(status='Delivered').select_related(
        'supplier', 'requested_by', 'approved_by'
    ).order_by('-order_date')
    
    # Filter by department if provided
    department_filter = request.GET.get('department')
    if department_filter:
        delivered_pos = delivered_pos.filter(department=department_filter)
    
    # Filter by finance status
    finance_status = request.GET.get('finance_status')
    if finance_status == 'ready':
        delivered_pos = delivered_pos.filter(finance_ready=True)
    elif finance_status == 'not_ready':
        delivered_pos = delivered_pos.filter(finance_ready=False)
    
    # Filter by amount range
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    if min_amount:
        delivered_pos = delivered_pos.filter(total_amount__gte=min_amount)
    if max_amount:
        delivered_pos = delivered_pos.filter(total_amount__lte=max_amount)
    
    # Group by department for cost analysis
    by_department = {}
    for po in delivered_pos:
        dept = po.department or 'Unknown'
        if dept not in by_department:
            by_department[dept] = {'count': 0, 'total': 0}
        by_department[dept]['count'] += 1
        by_department[dept]['total'] += float(po.total_amount)
    
    # Pagination
    paginator = Paginator(delivered_pos, 20)
    page = request.GET.get('page')
    
    try:
        purchase_orders = paginator.page(page)
    except PageNotAnInteger:
        purchase_orders = paginator.page(1)
    except EmptyPage:
        purchase_orders = paginator.page(paginator.num_pages)
    
    context = {
        'purchase_orders': purchase_orders,
        'by_department': by_department,
        'total_value': sum(po.total_amount for po in purchase_orders),
    }
    return render(request, 'procurement/finance_pos.html', context)


@login_required
@group_required('Finance')
def po_to_expense(request, pk):
    """Mark PO as paid/expensed (Finance action)"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status != 'Delivered':
        messages.error(request, 'Only delivered orders can be marked as expenses.')
        return redirect('procurement:finance_purchase_orders')
    
    # Add note that it's been processed as expense
    purchase_order.notes = f"{purchase_order.notes}\n[Processed as expense by {request.user.username} on {datetime.now().strftime('%Y-%m-%d')}]"
    purchase_order.save()
    
    # 🔴 AUDIT ADD - After this line
    audit_log(
        user=request.user,
        action='UPDATE',
        module='PROCUREMENT',
        object_type='PurchaseOrder',
        object_id=purchase_order.id,
        description=f'Marked Purchase Order as expense: {purchase_order.po_number} (Amount: Tsh {purchase_order.total_amount:,.2f})',
        request=request
    )
    
    messages.success(request, f'Purchase Order {purchase_order.po_number} marked as expense!')
    return redirect('procurement:finance_purchase_orders')