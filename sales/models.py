# cornelsimba/sales/models.py - FULLY UPDATED AND CORRECTED VERSION
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from inventory.models import Item
from decimal import Decimal

User = get_user_model()

class Customer(models.Model):
    """Customer information for sales tracking"""
    CUSTOMER_TYPES = [
        ('INDIVIDUAL', 'Individual'),
        ('COMPANY', 'Company'),
        ('GOVERNMENT', 'Government'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='COMPANY')
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="TIN/VAT Number")
    
    # Credit terms
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount in Tsh")
    payment_terms = models.CharField(max_length=100, blank=True, null=True, 
                                     help_text="e.g., Net 30, Cash on Delivery")
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    @property
    def credit_limit_display(self):
        """Display credit limit with Tsh symbol"""
        return f"Tsh {self.credit_limit:,.2f}"


class Sale(models.Model):
    """Main sales transaction model"""
    SALE_TYPES = [
        ('CASH', 'Cash Sale'),
        ('CREDIT', 'Credit Sale'),
        ('CONSIGNMENT', 'Consignment'),
        ('RETURN', 'Return Sale'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('STOCK_OUT_PENDING', 'Stock Out Pending'),
    ]
    
    # Sale information
    sale_number = models.CharField(max_length=50, unique=True, help_text="Auto-generated sale number")
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='CASH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Customer information
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    
    # Pricing (in Tsh)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount in Tsh")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in Tsh")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in Tsh")
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount in Tsh")
    
    # Payment tracking
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount in Tsh")
    balance_due = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount in Tsh")
    is_paid = models.BooleanField(default=False)
    
    # Currency information
    currency = models.CharField(max_length=10, default='Tsh', choices=[
        ('Tsh', 'Tanzanian Shillings'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ])
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0, 
                                       help_text="Exchange rate to Tsh (1 foreign currency = X Tsh)")
    
    # Delivery information
    delivery_address = models.TextField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    delivery_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('DELIVERED', 'Delivered'),
        ('PARTIAL', 'Partially Delivered'),
    ], default='PENDING')
    
    # Reference to inventory stock out
    inventory_stock_out = models.OneToOneField(
        'inventory.StockOut',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_relation',
        help_text="Linked inventory stock out record"
    )
    
    # Stock out status tracking
    is_stock_out_requested = models.BooleanField(default=False)
    stock_out_request_date = models.DateTimeField(null=True, blank=True)
    stock_out_processed_date = models.DateTimeField(null=True, blank=True)
    
    # Approval and tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sales')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_sales')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sale_date = models.DateField(default=timezone.now)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    terms_conditions = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Sale {self.sale_number} - {self.customer.name} - Tsh {self.net_amount:,.2f}"
    
class Meta:
    ordering = ['-created_at']
    verbose_name = 'Sale'
    verbose_name_plural = 'Sales'
    indexes = [
        models.Index(fields=['sale_date']),
        models.Index(fields=['status']),
        models.Index(fields=['created_at']),
        models.Index(fields=['customer']),
    ]


    def clean(self):
        """Validate sale before saving"""
        if self.net_amount < 0:
            raise ValidationError('Net amount cannot be negative')
        
        if self.balance_due < 0:
            raise ValidationError('Balance due cannot be negative')
        
        # Validate payment status
        if self.is_paid and self.balance_due > 0:
            raise ValidationError('Cannot mark as paid when balance is due')
    
    def save(self, *args, **kwargs):
        # Generate sale number if new
        if not self.sale_number:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.sale_number = f"SALE-{timestamp}"
        
        # Calculate balance
        self.balance_due = self.net_amount - self.amount_paid
        self.is_paid = self.balance_due <= Decimal('0.01')  # Allow small tolerance
        
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calculate totals from sale items"""
        try:
            items = self.items.all()
            
            total_amount = Decimal('0')
            tax_amount = Decimal('0')
            
            for item in items:
                total_amount += item.total_price or Decimal('0')
                tax_amount += item.tax_amount or Decimal('0')
            
            self.total_amount = total_amount
            self.tax_amount = tax_amount
            self.net_amount = total_amount + tax_amount - self.discount_amount
            self.balance_due = self.net_amount - self.amount_paid
            self.is_paid = self.balance_due <= Decimal('0.01')
            
            # Save only the calculated fields
            self.save(update_fields=[
                'total_amount', 'tax_amount', 'net_amount', 
                'balance_due', 'is_paid', 'updated_at'
            ])
            
        except Exception as e:
            # If we can't access items (e.g., sale not saved yet), do nothing
            pass
    
    def calculate_totals_from_values(self, total_amount, tax_amount):
        """Calculate totals from provided values (used when sale doesn't have PK yet)"""
        self.total_amount = total_amount or Decimal('0')
        self.tax_amount = tax_amount or Decimal('0')
        self.net_amount = self.total_amount + self.tax_amount - self.discount_amount
        self.balance_due = self.net_amount - self.amount_paid
        self.is_paid = self.balance_due <= Decimal('0.01')
    
    @property
    def item_count(self):
        """Number of items in sale"""
        return self.items.count()
    
    @property
    def net_amount_display(self):
        """Display net amount with currency symbol"""
        if self.currency == 'Tsh':
            return f"Tsh {self.net_amount:,.2f}"
        elif self.currency == 'USD':
            usd_amount = self.net_amount / self.exchange_rate if self.exchange_rate != Decimal('0') else Decimal('0')
            return f"${usd_amount:,.2f} (Tsh {self.net_amount:,.2f})"
        else:
            eur_amount = self.net_amount / self.exchange_rate if self.exchange_rate != Decimal('0') else Decimal('0')
            return f"€{eur_amount:,.2f} (Tsh {self.net_amount:,.2f})"
    
    def create_stock_out_request(self, user):
        """
        Create a PENDING stock out request (does NOT deduct stock)
        Inventory team must approve it first
        """
        from inventory.models import StockOut
        
        # Check if already requested
        if self.inventory_stock_out:
            raise ValidationError(f"Stock out already exists for this sale (ID: {self.inventory_stock_out.id})")
        
        if not self.items.exists():
            raise ValidationError("Cannot create stock out for sale with no items")
        
        # Check stock availability first
        is_available, message = self.check_stock_availability()
        if not is_available:
            raise ValidationError(f"Cannot request stock out: {message}")
        
        # Create stock out record with PENDING status
        # Note: For simplicity, we create one stock out per sale. 
        # In a real system, you might want one stock out per item.
        first_item = self.items.first()
        stock_out = StockOut.objects.create(
            item=first_item.item,
            quantity=first_item.quantity,
            issued_to=self.customer.name,
            purpose='SALE',
            reference=self.sale_number,
            notes=f"Sale request #{self.sale_number} - Total: Tsh {self.net_amount:,.2f}",
            status='pending',  # PENDING - not approved yet
            created_by=user,
            issued_by=user.get_full_name() or user.username,
            sale_reference=self.sale_number,
            linked_sale=self
        )
        
        # Update sale status and tracking
        self.inventory_stock_out = stock_out
        self.is_stock_out_requested = True
        self.stock_out_request_date = timezone.now()
        self.status = 'STOCK_OUT_PENDING'
        
        self.save(update_fields=[
            'inventory_stock_out', 'is_stock_out_requested',
            'stock_out_request_date', 'status', 'updated_at'
        ])
        
        return stock_out
    
    def check_stock_availability(self):
        """
        Check if there's enough stock for this sale
        Returns: (bool, str) - (is_available, message)
        """
        stock_issues = []
        
        for sale_item in self.items.all():
            if sale_item.quantity > sale_item.item.quantity:
                stock_issues.append(
                    f"{sale_item.item.name}: Need {sale_item.quantity}, Available {sale_item.item.quantity}"
                )
        
        if stock_issues:
            return False, "Insufficient stock: " + "; ".join(stock_issues)
        return True, "Stock available for all items"
    
    def mark_as_approved(self, user):
        """Mark sale as approved"""
        if self.status != 'DRAFT' and self.status != 'PENDING':
            raise ValidationError(f"Sale is already {self.get_status_display()}")
        
        self.status = 'APPROVED'
        self.approved_by = user
        self.save(update_fields=['status', 'approved_by', 'updated_at'])
        
        return self
    
    def mark_as_completed(self, user):
        """Mark sale as completed (after stock out)"""
        if self.status != 'APPROVED' and self.status != 'STOCK_OUT_PENDING':
            raise ValidationError(f"Cannot complete sale in {self.get_status_display()} status")
        
        self.status = 'COMPLETED'
        self.stock_out_processed_date = timezone.now()
        self.save(update_fields=['status', 'stock_out_processed_date', 'updated_at'])
        
        return self
    
    @property
    def can_request_stock_out(self):
     """Check if sale can request stock out - SIMPLIFIED"""
     return self.status == 'APPROVED'

    
    @property
    def has_pending_stock_out(self):
        """Check if sale has pending stock out"""
        return (
            self.inventory_stock_out and 
            self.inventory_stock_out.status == 'pending'
        )
    
    @property
    def has_approved_stock_out(self):
        """Check if sale has approved stock out"""
        return (
            self.inventory_stock_out and 
            self.inventory_stock_out.status == 'approved'
        )
    
    def get_stock_out_status(self):
        """Get stock out status"""
        if not self.inventory_stock_out:
            return "Not Requested"
        
        status = self.inventory_stock_out.status
        if status == 'pending':
            return "Pending Approval"
        elif status == 'approved':
            return "Approved & Processed"
        elif status == 'rejected':
            return "Rejected"
        else:
            return status.capitalize()


class SaleItem(models.Model):
    """Individual items in a sale"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0.001)])
    
    # Pricing (in Tsh)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)], help_text="Price in Tsh per unit")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Tax rate in percentage (e.g., 18 for 18%)")
    
    # Calculated fields (in Tsh)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in Tsh")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in Tsh")
    
    # Currency information
    currency = models.CharField(max_length=10, default='Tsh')
    
    # Stock tracking
    is_stocked_out = models.BooleanField(default=False)
    stock_out_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.item.name} x {self.quantity} in Sale {self.sale.sale_number}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
        unique_together = ['sale', 'item']
        indexes = [
            models.Index(fields=['item']),
            models.Index(fields=['sale']),
            models.Index(fields=['created_at']),
        ]

    
    def clean(self):
        """Validate sale item"""
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than 0')
        
        if self.unit_price <= 0:
            raise ValidationError('Unit price must be greater than 0')
        
        # Check stock availability if item exists and not editing
        if self.pk is None and hasattr(self, 'item'):
            if self.quantity > self.item.quantity:
                raise ValidationError(
                    f"Insufficient stock. Available: {self.item.quantity}, Requested: {self.quantity}"
                )
    
    def save(self, *args, **kwargs):
        # Calculate totals
        self.total_price = (self.quantity or Decimal('0')) * (self.unit_price or Decimal('0'))
        self.tax_amount = self.total_price * ((self.tax_rate or Decimal('0')) / Decimal('100'))
        
        # If this is a new item and sale already has approved stock out, mark as stocked out
        if self.sale and self.sale.has_approved_stock_out:
            self.is_stocked_out = True
            self.stock_out_date = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update sale totals if sale exists
        if self.sale and self.sale.pk:
            try:
                self.sale.calculate_totals()
            except Exception:
                # If calculation fails, don't break the save
                pass
    
    @property
    def total_price_display(self):
        """Display total price with Tsh symbol"""
        return f"Tsh {self.total_price:,.2f}"
    
    @property
    def unit_price_display(self):
        """Display unit price with Tsh symbol"""
        return f"Tsh {self.unit_price:,.2f}"
    
    def mark_as_stocked_out(self):
        """Mark this item as stocked out"""
        self.is_stocked_out = True
        self.stock_out_date = timezone.now()
        self.save(update_fields=['is_stocked_out', 'stock_out_date'])


class Payment(models.Model):
    """Payment records for sales"""
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT_CARD', 'Credit Card'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)], help_text="Amount in Tsh")
    currency = models.CharField(max_length=10, default='Tsh')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='COMPLETED')
    
    # Payment details
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Dates
    payment_date = models.DateField(default=timezone.now)
    received_by = models.CharField(max_length=100, blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment Tsh {self.amount:,.2f} for {self.sale.sale_number}"
    


    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['sale']),
        ]

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('Payment amount must be greater than 0')

        if self.sale_id and self.amount > self.sale.balance_due:
            raise ValidationError(
                f'Payment amount cannot exceed balance due (Tsh {self.sale.balance_due:,.2f})'
            )

    def save(self, *args, **kwargs):
        if self.amount < 0:
            self.amount = abs(self.amount)
        super().save(*args, **kwargs)

    @property
    def amount_display(self):
        return f"Tsh {self.amount:,.2f}"


class SaleReturn(models.Model):
    """Handle returns and refunds"""
    RETURN_REASONS = [
        ('DAMAGED', 'Damaged Goods'),
        ('WRONG_ITEM', 'Wrong Item Delivered'),
        ('QUALITY', 'Quality Issues'),
        ('CUSTOMER_CHANGE', 'Customer Changed Mind'),
        ('OTHER', 'Other'),
    ]
    
    original_sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    return_number = models.CharField(max_length=50, unique=True)
    reason = models.CharField(max_length=50, choices=RETURN_REASONS, default='OTHER')
    
    # Refund information
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount in Tsh")
    refund_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REFUNDED', 'Refunded'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')
    
    # Stock handling
    stock_returned = models.BooleanField(default=False)
    return_to_inventory = models.BooleanField(default=True)
    
    # Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Return {self.return_number} for Sale {self.original_sale.sale_number}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sale Return'
        verbose_name_plural = 'Sale Returns'
    
    def save(self, *args, **kwargs):
        if not self.return_number:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.return_number = f"RET-{timestamp}"
        super().save(*args, **kwargs)
    
    def create_stock_in_from_return(self, user):
        """
        Create stock in record when returned items go back to inventory
        """
        if not self.stock_returned and self.return_to_inventory:
            from inventory.models import StockIn
            
            # Get all items from original sale
            original_items = self.original_sale.items.all()
            
            for sale_item in original_items:
                StockIn.objects.create(
                    item=sale_item.item,
                    quantity=sale_item.quantity,
                    source='Return',
                    supplier=self.original_sale.customer.name,
                    reference=f"Return {self.return_number}",
                    notes=f"Return from sale {self.original_sale.sale_number}. Reason: {self.get_reason_display()}",
                    created_by=user,
                    received_by=user.get_full_name() or user.username,
                    status='approved'
                )
            
            self.stock_returned = True
            self.save(update_fields=['stock_returned', 'updated_at'])
            
            return True
        return False