from .models import Sale

def sales_sidebar_context(request):
    """Add sidebar data to all sales templates"""
    if request.resolver_match and request.resolver_match.app_name == 'sales':
        pending_stock_out_count = Sale.objects.filter(
            status='STOCK_OUT_PENDING'
        ).count()
        
        return {
            'pending_stock_out_count': pending_stock_out_count,
        }
    return {}