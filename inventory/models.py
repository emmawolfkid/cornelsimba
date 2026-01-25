# cornelsimba/inventory/models.py - FIXED VERSION
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone 

User = get_user_model()

class Item(models.Model):
    CATEGORY_CHOICES = [
        ('RAW_MATERIALS', 'Raw Materials'),
        ('CHEMICALS', 'Chemicals'),
        ('FINISHED_GOODS', 'Finished Goods'),
        ('OTHERS', 'Others'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='RAW_MATERIALS')
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Stock Keeping Unit")
    unit_of_measure = models.CharField(max_length=20, default='kg', help_text="e.g., kg, pcs, liter, box")
    
    # Stock tracking
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=15, decimal_places=3, default=10)
    minimum_stock = models.DecimalField(max_digits=15, decimal_places=3, default=5)
    
    # Pricing (for sales integration)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Cost price in Tsh")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Selling price in Tsh")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit_of_measure})"
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='unique_item_name',
                condition=models.Q(is_active=True),
            )
        ]
    
    def clean(self):
        """Validate no duplicate names (case-insensitive)"""
        super().clean()
        
        if self.name and self.is_active:
            # Clean the name
            clean_name = self.name.strip()
            
            # Check for existing active items with same name (case-insensitive)
            query = Item.objects.filter(
                name__iexact=clean_name,
                is_active=True
            )
            
            if self.pk:
                query = query.exclude(pk=self.pk)
            
            if query.exists():
                existing_item = query.first()
                raise ValidationError({
                    'name': f"Item '{clean_name}' already exists as '{existing_item.name}' (ID: {existing_item.id}). Please use the existing item."
                })
    
    def save(self, *args, **kwargs):
        # Normalize name: trim and proper capitalization
        if self.name:
            # Remove extra spaces, proper capitalization
            self.name = ' '.join(word.strip().title() for word in self.name.split())
        
        # Fix for category field - map 'Finished Goods' to 'FINISHED_GOODS'
        if hasattr(self, 'category') and self.category:
            # Convert 'Finished Goods' to 'FINISHED_GOODS' if needed
            if self.category == 'Finished Goods':
                self.category = 'FINISHED_GOODS'
            # Also check for other possible variations
            elif self.category.lower() == 'finished goods':
                self.category = 'FINISHED_GOODS'
        
        # Run validation
        self.full_clean()
        
        # Save
        super().save(*args, **kwargs)
    
    def update_quantity(self):
        """Recalculate quantity based on all transactions"""
        stock_in_total = self.stock_ins.aggregate(total=models.Sum('quantity'))['total'] or 0
        stock_out_total = self.stock_outs.aggregate(total=models.Sum('quantity'))['total'] or 0
        adjustment_total = self.stock_adjustments.filter(is_approved=True).aggregate(
            total=models.Sum('adjustment_quantity')
        )['total'] or 0
        
        self.quantity = stock_in_total - stock_out_total + adjustment_total
        self.save(update_fields=['quantity'])
    
    @property
    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.quantity <= self.reorder_level
    
    @property
    def is_critical_stock(self):
        """Check if stock is below minimum level"""
        return self.quantity <= self.minimum_stock
    
    @property
    def status(self):
        """Get stock status"""
        if self.quantity <= self.minimum_stock:
            return 'Critical'
        elif self.quantity <= self.reorder_level:
            return 'Low'
        else:
            return 'Good'
    
    @property
    def selling_price_display(self):
        """Display selling price with Tsh symbol"""
        return f"Tsh {self.selling_price:,.2f}"
    
    @property
    def purchase_price_display(self):
        """Display purchase price with Tsh symbol"""
        return f"Tsh {self.purchase_price:,.2f}"


class StockIn(models.Model):
    SOURCE_CHOICES = [
        ('Purchase', 'Purchase Order'),
        ('Return', 'Customer Return'),
        ('Production', 'Production'),
        ('Adjustment', 'Stock Adjustment'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='stock_ins')
    quantity = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(0.001)])
    
    # Source information
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Purchase')
    supplier = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True, help_text="PO Number, GRN, etc.")
    
    # Approval tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_stock_ins')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_stock_ins')
    received_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def clean(self):
        """Validate before saving"""
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0.'})
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Only update stock if approved
        if self.status == 'approved':
            if not is_new:
                # This is an update - need to adjust stock properly
                old_stock_in = StockIn.objects.get(pk=self.pk)
                old_quantity = old_stock_in.quantity
                
                # Calculate the difference
                quantity_diff = self.quantity - old_quantity
                
                # If item changed, handle both old and new items
                if old_stock_in.item.id != self.item.id:
                    # Remove from old item
                    old_stock_in.item.quantity -= old_quantity
                    old_stock_in.item.save()
                    
                    # Add to new item
                    self.item.quantity += self.quantity
                else:
                    # Same item, adjust by the difference
                    self.item.quantity += quantity_diff
            else:
                # New record - just add to item
                self.item.quantity += self.quantity
            
            # Save the item
            self.item.save()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # When deleting, remove stock from item if approved
        if self.status == 'approved':
            self.item.quantity -= self.quantity
            self.item.save()
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item.name} - {self.quantity} in from {self.supplier or self.source}"
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Stock In'
        verbose_name_plural = 'Stock Ins'


class StockOut(models.Model):
    PURPOSE_CHOICES = [
        ('SALE', 'Sale'),
        ('TRANSFER', 'Transfer to Another Location'),
        ('INTERNAL_USE', 'Internal Use'),
        ('DAMAGE', 'Damage / Loss'),
        ('SAMPLE', 'Sample / Testing'),
        ('RETURN', 'Return to Supplier'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='stock_outs')
    quantity = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(0.001)])
    
    # Destination information
    issued_to = models.CharField(max_length=100, blank=True, null=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='INTERNAL_USE')
    reference = models.CharField(max_length=100, blank=True, null=True, help_text="Sales Order, Requisition, etc.")
    
    # Sale reference fields - ADD THESE FOR SALES INTEGRATION
    sale_reference = models.CharField(max_length=100, blank=True, null=True, 
                                      help_text="Sale number if purpose is SALE")
    linked_sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='stock_outs')
    
    # Approval tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_stock_outs')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_stock_outs')
    issued_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def clean(self):
        """Better stock availability validation"""
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0.'})
        
        # Check stock availability (only if approved)
        if self.item and self.status == 'approved':
            available = self.item.quantity
            if self.quantity > available:
                raise ValidationError({
                    'quantity': f'Insufficient stock! Available: {available} {self.item.unit_of_measure}'
                })
    
    def save(self, *args, **kwargs):
        # Validate before saving
        self.full_clean()
        
        is_new = self.pk is None
        
        # Only update stock if approved
        if self.status == 'approved':
            if not is_new:
                # This is an update - need to adjust stock properly
                old_stock_out = StockOut.objects.get(pk=self.pk)
                old_quantity = old_stock_out.quantity
                
                # Calculate the difference (add back old, subtract new)
                quantity_diff = old_quantity - self.quantity
                
                # If item changed, handle both old and new items
                if old_stock_out.item.id != self.item.id:
                    # Add back to old item
                    old_stock_out.item.quantity += old_quantity
                    old_stock_out.item.save()
                    
                    # Subtract from new item
                    self.item.quantity -= self.quantity
                else:
                    # Same item, adjust by the difference
                    self.item.quantity += quantity_diff
            else:
                # New record - subtract from item
                self.item.quantity -= self.quantity
            
            # Save the item
            self.item.save()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # When deleting, add stock back to item if approved
        if self.status == 'approved':
            self.item.quantity += self.quantity
            self.item.save()
        super().delete(*args, **kwargs)
    
    def __str__(self):
        purpose_display = self.get_purpose_display()
        if self.purpose == 'SALE' and self.sale_reference:
            return f"{self.item.name} - {self.quantity} out for {purpose_display} ({self.sale_reference})"
        return f"{self.item.name} - {self.quantity} out for {purpose_display}"
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Stock Out'
        verbose_name_plural = 'Stock Outs'
    
    @property
    def is_sale_related(self):
        """Check if this stock out is related to a sale"""
        return self.purpose == 'SALE' and (self.linked_sale or self.sale_reference)
    
    @property
    def sale_info(self):
        """Get sale information if available"""
        if self.linked_sale:
            return {
                'sale_number': self.linked_sale.sale_number,
                'customer': self.linked_sale.customer.name,
                'amount': self.linked_sale.net_amount_display,
            }
        elif self.sale_reference:
            return {'sale_number': self.sale_reference}
        return None


class StockAdjustment(models.Model):
    """For correcting stock errors - requires approval"""
    
    ADJUSTMENT_TYPE_CHOICES = [
        ('ERROR_CORRECTION', 'Data Entry Error'),
        ('MEASUREMENT_CORRECTION', 'Measurement Correction'),
        ('LOSS', 'Loss / Spillage / Theft'),
        ('SHRINKAGE', 'Natural Shrinkage'),
        ('GAIN', 'Stock Gain'),
        ('PHYSICAL_COUNT', 'Physical Count Difference'),
        ('OTHER', 'Other'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='stock_adjustments')
    adjustment_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=3,
        help_text="Positive to add stock, negative to reduce"
    )
    
    # Reason information
    adjustment_type = models.CharField(max_length=50, choices=ADJUSTMENT_TYPE_CHOICES)
    reason = models.TextField(help_text="Detailed explanation of why adjustment is needed")
    reference_stock_in = models.ForeignKey(
        StockIn, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="If this adjustment is correcting a specific Stock In"
    )
    
    # Approval workflow
    status = models.CharField(max_length=20, choices=StockIn.STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_adjustments')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_adjustments')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_adjustments')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
    
    def __str__(self):
        sign = '+' if self.adjustment_quantity > 0 else ''
        return f"{self.item.name}: {sign}{self.adjustment_quantity} ({self.get_adjustment_type_display()})"
    
    def clean(self):
        if self.adjustment_quantity == 0:
            raise ValidationError({'adjustment_quantity': 'Adjustment quantity cannot be zero'})
        
        # Check if negative adjustment would make stock negative
        if self.adjustment_quantity < 0 and self.item:
            current_stock = self.item.quantity
            new_stock = current_stock + self.adjustment_quantity
            if new_stock < 0:
                raise ValidationError({
                    'adjustment_quantity': f'Adjustment would make stock negative. Current: {current_stock}'
                })
    
    def save(self, *args, **kwargs):
        # Only update stock if approved
        if self.status == 'approved' and not self.approved_at:
            self.item.quantity += self.adjustment_quantity
            self.item.save()
            self.approved_at = timezone.now()
        elif self.status == 'approved' and self.approved_at:
            # Already approved, don't update stock again
            pass
        
        super().save(*args, **kwargs)
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'


class StockHistory(models.Model):
    TRANSACTION_CHOICES = [
        ('STOCK_IN', 'Stock In'),
        ('STOCK_OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='stock_history')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_CHOICES)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    previous_quantity = models.DecimalField(max_digits=15, decimal_places=3)
    new_quantity = models.DecimalField(max_digits=15, decimal_places=3)
    
    # Reference to specific transaction
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    reference_model = models.CharField(max_length=50, null=True, blank=True)
    
    # Details
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock History'
        verbose_name_plural = 'Stock Histories'
    
    def __str__(self):
        return f"{self.item.name} - {self.transaction_type} - {self.quantity}"