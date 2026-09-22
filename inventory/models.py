from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductStatus(models.TextChoices):
    IN_STOCK = 'In Stock', 'In Stock'
    OUT_OF_STOCK = 'Out of Stock', 'Out of Stock'
    LOW_STOCK = 'Low Stock', 'Low Stock'


class Product(models.Model):
    """
    Master Product definition.
    Serial numbers are NOT required on creation; serial numbers are optional at checkout.
    """
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    sku = models.CharField(max_length=100, blank=True, default='', db_index=True)
    size = models.CharField(max_length=100, blank=True, default='', help_text="Size / Model Specs")
    description = models.TextField(blank=True, default='')
    # Kept for backward-compatibility if existing migrations refer to it
    serial_number = models.CharField(max_length=100, blank=True, default='', db_index=True)
    account_number = models.CharField(max_length=100, blank=True, default='', db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_added'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def current_selling_price(self):
        if hasattr(self, 'stock') and self.stock:
            return self.stock.selling_price
        return Decimal('0.00')

    @property
    def available_quantity(self):
        if hasattr(self, 'stock') and self.stock:
            return self.stock.quantity_available
        return 0

    @property
    def is_in_stock(self):
        return self.available_quantity > 0

    @property
    def stock_value(self):
        """Total inventory selling valuation for this product."""
        return self.current_selling_price * Decimal(str(self.available_quantity))

    @property
    def total_cost_value(self):
        """Total FIFO inventory cost value from active remaining batches."""
        total = Decimal('0.00')
        for b in self.batches.filter(is_active=True, quantity_remaining__gt=0):
            total += b.cost_price * Decimal(str(b.quantity_remaining))
        return total


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def invoice_count(self):
        return self.batches.values('supplier_invoice_number').distinct().count()

    @property
    def batch_count(self):
        return self.batches.count()


class Stock(models.Model):
    """
    Stock record keeping selling price and aggregate available quantities for each Product.
    """
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock'
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current Selling Price (USD)"
    )
    quantity_available = models.PositiveIntegerField(
        default=0,
        help_text="Current total available quantity from active batches"
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Threshold below which stock is flagged as Low Stock"
    )
    reorder_quantity = models.PositiveIntegerField(
        default=5,
        help_text="Reorder quantity threshold for low stock notification alerts"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'

    def __str__(self):
        return f"{self.product.name} — Qty: {self.quantity_available} @ ${self.selling_price}"

    @property
    def is_low_stock(self):
        return self.quantity_available <= self.reorder_quantity

    def recalculate_quantity(self):
        """Recalculate available quantity strictly from active non-exhausted batches."""
        total = self.product.batches.filter(is_active=True).aggregate(
            total_rem=models.Sum('quantity_remaining')
        )['total_rem'] or 0
        self.quantity_available = total
        self.save(update_fields=['quantity_available', 'updated_at'])
        return self.quantity_available


class StockBatch(models.Model):
    """
    Batch record keeping quantities and unit cost prices when invoices are received.
    Deducted via FIFO when items are sold.
    A single stock/product can have multiple batches.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )
    supplier_ref = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches',
        help_text="Direct link to registered Supplier"
    )
    supplier_invoice_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        db_index=True,
        help_text="Supplier Invoice Reference / Number"
    )

    supplier_name = models.CharField(
        max_length=150,
        blank=True,
        default=''
    )
    date_received = models.DateField(
        default=timezone.now,
        db_index=True
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Unit Purchase Cost (USD)"
    )
    quantity_received = models.PositiveIntegerField(
        default=1,
        help_text="Initial quantity received"
    )
    quantity_remaining = models.PositiveIntegerField(
        default=1,
        help_text="Quantity currently available in this batch"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True while quantity_remaining > 0"
    )
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Batch'
        verbose_name_plural = 'Stock Batches'
        ordering = ['date_received', 'id']

    def save(self, *args, **kwargs):
        if not self.stock_id and self.product_id:
            try:
                stock_obj, _ = Stock.objects.get_or_create(product_id=self.product_id)
                self.stock = stock_obj
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Batch #{self.id}: {self.product.name} ({self.quantity_remaining}/{self.quantity_received} left @ ${self.cost_price})"

