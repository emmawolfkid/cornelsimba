# cornelsimba/inventory/views_sales.py - CREATE THIS FILE
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import StockOut, Item
from sales.models import Sale
import logging

logger = logging.getLogger(__name__)

@login_required
@permission_required('inventory.change_stockout', raise_exception=True)
def pending_sales_stockouts(request):
    """
    Show sales that need stock out processing
    """
    # Get stock outs that are pending and sale-related
    pending_stockouts = StockOut.objects.filter(
        status='pending',
        purpose='SALE',
        linked_sale__isnull=False
    ).select_related('item', 'linked_sale', 'linked_sale__customer')
    
    # Get sales that don't have stock outs yet
    sales_without_stockout = Sale.objects.filter(
        inventory_stock_out__isnull=True,
        status='APPROVED'  # Only approved sales
    ).select_related('customer')
    
    context = {
        'pending_stockouts': pending_stockouts,
        'sales_without_stockout': sales_without_stockout,
        'title': 'Sales Stock Out Requests'
    }
    return render(request, 'inventory/pending_sales_stockouts.html', context)

@login_required
@permission_required('inventory.change_stockout', raise_exception=True)
def approve_stockout(request, stockout_id):
    """
    Approve a stock out request
    """
    stockout = get_object_or_404(
        StockOut.objects.select_related('item', 'linked_sale'),
        id=stockout_id,
        status='pending'
    )
    
    try:
        # Check stock availability
        if stockout.quantity > stockout.item.quantity:
            messages.error(
                request,
                f"Insufficient stock! Available: {stockout.item.quantity}, "
                f"Requested: {stockout.quantity}"
            )
            return redirect('inventory:pending_sales_stockouts')
        
        # Approve the stock out
        stockout.status = 'approved'
        stockout.approved_by = request.user
        stockout.save()
        
        messages.success(
            request,
            f"Stock out approved for {stockout.item.name}. "
            f"Stock deducted: {stockout.quantity}"
        )
        
        # If there's a linked sale, mark it appropriately
        if stockout.linked_sale:
            sale = stockout.linked_sale
            # Update sale status if needed
            if sale.status == 'APPROVED':
                sale.status = 'COMPLETED'
                sale.save(update_fields=['status'])
        
    except ValidationError as e:
        messages.error(request, f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error approving stock out: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('inventory:pending_sales_stockouts')

@login_required
@permission_required('inventory.add_stockout', raise_exception=True)
def create_stockout_for_sale(request, sale_id):
    """
    Create stock out directly from inventory for a sale
    """
    sale = get_object_or_404(
        Sale.objects.select_related('customer').prefetch_related('items__item'),
        id=sale_id,
        inventory_stock_out__isnull=True
    )
    
    if request.method == 'POST':
        try:
            # Create stock out for each item in sale
            created_count = 0
            for sale_item in sale.items.all():
                # Check stock availability
                if sale_item.quantity > sale_item.item.quantity:
                    messages.warning(
                        request,
                        f"Skipping {sale_item.item.name}: Insufficient stock "
                        f"(Available: {sale_item.item.quantity})"
                    )
                    continue
                
                # Create stock out record
                StockOut.objects.create(
                    item=sale_item.item,
                    quantity=sale_item.quantity,
                    purpose='SALE',
                    issued_to=sale.customer.name,
                    reference=sale.sale_number,
                    notes=f"From sale #{sale.sale_number} - Item: {sale_item.item.name}",
                    status='approved',
                    created_by=request.user,
                    issued_by=request.user.get_full_name() or request.user.username,
                    sale_reference=sale.sale_number,
                    linked_sale=sale
                )
                created_count += 1
            
            if created_count > 0:
                messages.success(
                    request,
                    f"Created {created_count} stock out record(s) for sale #{sale.sale_number}"
                )
                # Refresh sale to get updated stock out
                sale.refresh_from_db()
                
            return redirect('inventory:pending_sales_stockouts')
            
        except Exception as e:
            logger.error(f"Error creating stock outs: {str(e)}")
            messages.error(request, f"Error: {str(e)}")
    
    context = {
        'sale': sale,
        'sale_items': sale.items.all(),
        'title': f'Create Stock Out for Sale #{sale.sale_number}'
    }
    return render(request, 'inventory/create_stockout_for_sale.html', context)