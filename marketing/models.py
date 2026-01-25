from django.db import models
from hr.models import Employee
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('Corporate', 'Corporate'),
        ('Government', 'Government'),
        ('Individual', 'Individual'),
        ('Reseller', 'Reseller'),
    ]
    
    name = models.CharField(max_length=100)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='Corporate')
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    tin_number = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_terms = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.customer_type})"
    
    class Meta:
        ordering = ['name']
    
    @property
    def total_contract_value(self):
        """Total value of all contracts with this customer"""
        from django.db.models import Sum
        return self.contracts.aggregate(total=Sum('value'))['total'] or 0
    
    @property
    def active_contracts_count(self):
        """Count of active contracts"""
        today = timezone.now().date()
        return self.contracts.filter(end_date__gte=today).count()


class Contract(models.Model):
    CONTRACT_TYPES = [
        ('Sales', 'Sales Agreement'),
        ('Service', 'Service Agreement'),
        ('Maintenance', 'Maintenance Contract'),
        ('Lease', 'Lease Agreement'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Active', 'Active'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='contracts')
    contract_number = models.CharField(max_length=20, unique=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES, default='Sales')
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    
    # HR Integration: Account manager/sales person
    account_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_contracts'
    )
    
    # Finance tracking
    payment_terms = models.TextField(blank=True, null=True)
    renewal_date = models.DateField(null=True, blank=True, help_text="Date to review for renewal")
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate contract dates"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError({'end_date': 'End date must be after start date.'})
    
    def save(self, *args, **kwargs):
        # Auto-generate contract number if not provided
        if not self.contract_number:
            from datetime import datetime
            date_part = datetime.now().strftime('%Y%m%d')
            last_contract = Contract.objects.filter(contract_number__contains=date_part).count()
            self.contract_number = f"CON-{date_part}-{last_contract + 1:04d}"
        
        # Update status based on dates
        today = timezone.now().date()
        if self.status != 'Cancelled':
            if today < self.start_date:
                self.status = 'Draft'
            elif self.start_date <= today <= self.end_date:
                self.status = 'Active'
            elif today > self.end_date:
                self.status = 'Expired'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer.name} (${self.value})"
    
    @property
    def is_active(self):
        """Check if contract is currently active"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.status == 'Active'
    
    @property
    def days_remaining(self):
        """Days remaining until contract ends"""
        if self.is_active:
            from datetime import date
            return (self.end_date - date.today()).days
        return 0
    
    @property
    def total_sales_value(self):
        """Total value of sales under this contract"""
        from django.db.models import Sum
        return self.sales.aggregate(total=Sum('total_price'))['total'] or 0
    
    @property
    def sales_count(self):
        """Number of sales under this contract"""
        return self.sales.count()
    
    class Meta:
        ordering = ['-start_date']


class Sale(models.Model):
    SALE_TYPES = [
        ('Product', 'Product Sale'),
        ('Service', 'Service Sale'),
        ('Installation', 'Installation'),
        ('Maintenance', 'Maintenance'),
        ('Other', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('Pending', 'Payment Pending'),
        ('Partial', 'Partial Payment'),
        ('Paid', 'Fully Paid'),
        ('Overdue', 'Overdue'),
    ]
    
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name='sales')
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='Product')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    # HR Integration: Who made the sale
    sales_person = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='sales_made'
    )
    
    # Payment tracking
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    invoice_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    sale_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    
    # Link to inventory items (optional)
    item_description = models.CharField(max_length=200, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate sale data"""
        # Ensure sale doesn't exceed contract value
        if self.contract and hasattr(self, 'total_price'):
            existing_sales_total = self.contract.total_sales_value
            if self.pk:  # If updating, subtract this sale's old value
                try:
                    old_sale = Sale.objects.get(pk=self.pk)
                    existing_sales_total -= old_sale.total_price
                except Sale.DoesNotExist:
                    pass
            
            if existing_sales_total + self.total_price > self.contract.value:
                raise ValidationError(
                    f'Sale amount (${self.total_price}) exceeds remaining contract value. '
                    f'Remaining: ${self.contract.value - existing_sales_total:.2f}'
                )
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Auto-generate invoice number if not provided
        if not self.invoice_number:
            from datetime import datetime
            date_part = datetime.now().strftime('%Y%m%d')
            last_invoice = Sale.objects.filter(invoice_number__contains=date_part).count()
            self.invoice_number = f"INV-{date_part}-{last_invoice + 1:04d}"
        
        # Set due date if not provided (30 days from sale date)
        if not self.due_date:
            from datetime import timedelta
            self.due_date = self.sale_date + timedelta(days=30)
        
        # Update payment status based on due date
        if self.payment_status != 'Paid' and self.due_date:
            today = timezone.now().date()
            if today > self.due_date:
                self.payment_status = 'Overdue'
        
        super().save(*args, **kwargs)
        
        # Auto-create Finance Income record for new sales
        if is_new:
            self.create_finance_income()
    
    def create_finance_income(self):
        """Create corresponding income record in Finance module"""
        try:
            from finance.models import Income
            
            Income.objects.create(
                source=f"Sale: {self.invoice_number}",
                amount=self.total_price,
                date=self.sale_date,
                income_type='Sales',
                department=self.sales_person.department if hasattr(self.sales_person, 'department') else 'Sales',
                reference=self.invoice_number,
                description=f"Sale from contract {self.contract.contract_number}\n"
                           f"Customer: {self.contract.customer.name}\n"
                           f"Sales Person: {self.sales_person.full_name}"
            )
        except ImportError:
            # Finance module not installed yet
            pass
        except Exception as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create finance income for sale {self.id}: {e}")
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    @property
    def is_overdue(self):
        """Check if sale payment is overdue"""
        if self.payment_status == 'Overdue':
            return True
        if self.due_date and self.payment_status != 'Paid':
            today = timezone.now().date()
            return today > self.due_date
        return False
    
    @property
    def days_overdue(self):
        """Days overdue if payment is late"""
        if self.is_overdue and self.due_date:
            today = timezone.now().date()
            return (today - self.due_date).days
        return 0
    
    def __str__(self):
        return f"{self.invoice_number} - ${self.total_price} ({self.contract.customer.name})"
    
    class Meta:
        ordering = ['-sale_date']