from django.db import models
from inventory.models import Item
from hr.models import Employee
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    tin_number = models.CharField(max_length=50, blank=True, null=True, default='')
    payment_terms = models.TextField(blank=True, null=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # Make nullable
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # Make nullable

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending', 'Pending Approval'),
        ('Approved', 'Approved'),
        ('Ordered', 'Ordered'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    
    # Make nullable for migration
    po_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    
    # HR Integration - Link to employees
    requested_by = models.ForeignKey(
        Employee, 
        on_delete=models.PROTECT, 
        related_name='requested_pos',
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_pos'
    )
    
    # Finance-ready fields
    department = models.CharField(max_length=50, blank=True, null=True, default='')
    cost_center = models.CharField(max_length=50, blank=True, null=True, default='')
    budget_code = models.CharField(max_length=50, blank=True, null=True, default='')
    
    order_date = models.DateField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    notes = models.TextField(blank=True, null=True, default='')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # Make nullable
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # Make nullable

    def save(self, *args, **kwargs):
        if not self.po_number:
            # Generate PO number: PO-YYYYMMDD-XXXX
            date_part = datetime.now().strftime('%Y%m%d')
            last_po = PurchaseOrder.objects.filter(po_number__contains=date_part).count()
            self.po_number = f"PO-{date_part}-{last_po + 1:04d}"
        
        # Auto-populate department from requested_by employee
        if self.requested_by and not self.department:
            self.department = self.requested_by.department
        
        super().save(*args, **kwargs)
        
        # Calculate total amount after saving
        if self.pk:
            total = sum(item.total_price for item in self.items.all())
            if total != self.total_amount:
                self.total_amount = total
                # Save again to update total_amount
                super().save(update_fields=['total_amount'])

    def __str__(self):
        po_num = self.po_number or f"PO-{self.id}"
        return f"{po_num} - {self.supplier.name} ({self.status})"
    
    @property
    def finance_ready(self):
        """Check if PO has all info needed for finance"""
        return all([
            self.department,
            self.cost_center or self.budget_code,
            self.total_amount > 0,
            self.status in ['Approved', 'Delivered']
        ])
    
    class Meta:
        ordering = ['-order_date']


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Remove editable=False for now
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item.name} - {self.quantity} x {self.unit_price}"
    
    class Meta:
        ordering = ['item__name']