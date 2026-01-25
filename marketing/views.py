# cornelsimba/marketing/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db import transaction
from functools import wraps
from datetime import date, timedelta
from .models import Customer, Contract, Sale
from .forms import CustomerForm, ContractForm, SaleForm

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
@group_required('Marketing')
def marketing_dashboard(request):
    # Get statistics - UPDATED model names
    total_clients = Customer.objects.filter(is_active=True).count()
    total_contracts = Contract.objects.filter(status='Active').count()
    
    # Get sales statistics
    total_sales = Sale.objects.count()
    recent_sales = Sale.objects.all().order_by('-sale_date')[:5]
    
    # Recent activities
    recent_clients = Customer.objects.all().order_by('-created_at')[:5]
    recent_contracts = Contract.objects.select_related('customer', 'account_manager').all().order_by('-created_at')[:5]
    
    # Contracts expiring soon (within 30 days)
    thirty_days_later = date.today() + timedelta(days=30)
    expiring_contracts = Contract.objects.filter(
        end_date__gte=date.today(),
        end_date__lte=thirty_days_later,
        status='Active'
    ).order_by('end_date')[:5]
    
    # Sales by status
    sales_by_status = Sale.objects.values('payment_status').annotate(
        count=Count('id'),
        total=Sum('total_price')
    ).order_by('-total')
    
    context = {
        # Statistics
        'total_clients': total_clients,
        'total_contracts': total_contracts,
        'total_sales': total_sales,
        
        # Recent activities
        'recent_clients': recent_clients,
        'recent_contracts': recent_contracts,
        'recent_sales': recent_sales,
        
        # Contract metrics
        'expiring_contracts': expiring_contracts,
        'sales_by_status': sales_by_status,
    }
    return render(request, 'marketing/dashboard.html', context)


@login_required
@group_required('Marketing')
def client_list(request):
    clients = Customer.objects.all().order_by('name')
    
    # Filters
    client_type = request.GET.get('type')
    is_active = request.GET.get('active')
    
    if client_type:
        clients = clients.filter(customer_type=client_type)
    if is_active:
        clients = clients.filter(is_active=(is_active == 'true'))
    
    context = {
        'clients': clients,
        'client_types': Customer.CUSTOMER_TYPES,
    }
    return render(request, 'marketing/client_list.html', context)


@login_required
@group_required('Marketing')
def client_detail(request, pk):
    client = get_object_or_404(Customer, pk=pk)
    contracts = client.contracts.all().order_by('-start_date')
    
    context = {
        'client': client,
        'contracts': contracts,
    }
    return render(request, 'marketing/client_detail.html', context)


@login_required
@group_required('Marketing')
def client_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client "{client.name}" created successfully!')
            return redirect('marketing:client_detail', pk=client.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'marketing/client_form.html', {'form': form})


@login_required
@group_required('Marketing')
def client_update(request, pk):
    client = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Client "{client.name}" updated successfully!')
            return redirect('marketing:client_detail', pk=client.pk)
    else:
        form = CustomerForm(instance=client)
    
    return render(request, 'marketing/client_form.html', {'form': form, 'client': client})


@login_required
@group_required('Marketing')
def contract_list(request):
    contracts = Contract.objects.select_related('customer', 'account_manager').all().order_by('-start_date')
    
    # Filters
    status = request.GET.get('status')
    contract_type = request.GET.get('type')
    
    if status:
        contracts = contracts.filter(status=status)
    if contract_type:
        contracts = contracts.filter(contract_type=contract_type)
    
    context = {
        'contracts': contracts,
        'status_choices': Contract.STATUS_CHOICES,
        'contract_types': Contract.CONTRACT_TYPES,
    }
    return render(request, 'marketing/contract_list.html', context)


@login_required
@group_required('Marketing')
def contract_detail(request, pk):
    contract = get_object_or_404(
        Contract.objects.select_related('customer', 'account_manager'),
        pk=pk
    )
    sales = contract.sales.select_related('sales_person').all().order_by('-sale_date')
    
    context = {
        'contract': contract,
        'sales': sales,
    }
    return render(request, 'marketing/contract_detail.html', context)


@login_required
@group_required('Marketing')
def contract_create(request):
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.save()
            messages.success(request, f'Contract {contract.contract_number} created successfully!')
            return redirect('marketing:contract_detail', pk=contract.pk)
    else:
        form = ContractForm()
    
    return render(request, 'marketing/contract_form.html', {'form': form})


@login_required
@group_required('Marketing')
def contract_update(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save()
            messages.success(request, f'Contract {contract.contract_number} updated successfully!')
            return redirect('marketing:contract_detail', pk=contract.pk)
    else:
        form = ContractForm(instance=contract)
    
    return render(request, 'marketing/contract_form.html', {'form': form, 'contract': contract})


@login_required
@group_required('Marketing')
def sale_list(request):
    sales = Sale.objects.select_related('contract', 'sales_person').all().order_by('-sale_date')
    
    # Filters
    status = request.GET.get('status')
    sale_type = request.GET.get('type')
    
    if status:
        sales = sales.filter(payment_status=status)
    if sale_type:
        sales = sales.filter(sale_type=sale_type)
    
    # Summary
    total_sales = sales.count()
    total_value = sum(sale.total_price for sale in sales)
    pending_sales = sales.filter(payment_status='Pending').count()
    
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_value': total_value,
        'pending_sales': pending_sales,
        'status_choices': Sale.PAYMENT_STATUS,
        'sale_types': Sale.SALE_TYPES,
    }
    return render(request, 'marketing/sale_list.html', context)


@login_required
@group_required('Marketing')
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('contract', 'sales_person'),
        pk=pk
    )
    
    context = {
        'sale': sale,
    }
    return render(request, 'marketing/sale_detail.html', context)


@login_required
@group_required('Marketing')
def sale_create(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save()
            messages.success(request, f'Sale {sale.invoice_number} created successfully!')
            return redirect('marketing:sale_detail', pk=sale.pk)
    else:
        form = SaleForm()
    
    return render(request, 'marketing/sale_form.html', {'form': form})


@login_required
@group_required('Marketing')
def sale_update(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            sale = form.save()
            messages.success(request, f'Sale {sale.invoice_number} updated successfully!')
            return redirect('marketing:sale_detail', pk=sale.pk)
    else:
        form = SaleForm(instance=sale)
    
    return render(request, 'marketing/sale_form.html', {'form': form, 'sale': sale})


@login_required
@group_required('Marketing')
def sales_report(request):
    """Sales performance reports"""
    # Time periods
    current_year = date.today().year
    
    # Sales by status
    sales_by_status = Sale.objects.values('payment_status').annotate(
        count=Count('id'),
        total_value=Sum('total_price')
    ).order_by('-total_value')
    
    # Sales by type
    sales_by_type = Sale.objects.values('sale_type').annotate(
        count=Count('id'),
        total_value=Sum('total_price')
    ).order_by('-total_value')
    
    # Monthly sales
    monthly_sales = []
    for month in range(1, 13):
        total = Sale.objects.filter(
            sale_date__year=current_year,
            sale_date__month=month
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        monthly_sales.append({
            'month': date(2000, month, 1).strftime('%B'),
            'total': total
        })
    
    # Top sales people
    top_salespeople = Sale.objects.values('sales_person__full_name').annotate(
        total_sales=Sum('total_price'),
        sale_count=Count('id')
    ).order_by('-total_sales')[:10]
    
    context = {
        'current_year': current_year,
        'sales_by_status': sales_by_status,
        'sales_by_type': sales_by_type,
        'monthly_sales': monthly_sales,
        'top_salespeople': top_salespeople,
        'total_sales': Sale.objects.count(),
        'total_sales_value': Sale.objects.aggregate(total=Sum('total_price'))['total'] or 0,
    }
    return render(request, 'marketing/sales_report.html', context)


# Remove all lead-related functions since you don't have a Lead model
# Remove: lead_list, lead_detail, lead_create, lead_update, lead_assign, 
# campaign_performance, and marketing_report (if it uses leads)

def sales_redirect(request):
    """Redirect placeholder"""
    messages.info(request, "This functionality is available in the Sales section.")
    return redirect('marketing:sale_list')