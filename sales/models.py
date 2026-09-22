import uuid
from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from inventory.models import Product, StockBatch

class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @classmethod
    def get_default_customer(cls):
        cust, _ = cls.objects.get_or_create(
            name="Walk-in Customer",
            defaults={"phone": "N/A", "address": "Store Counter"}
        )
        return cust


class PaymentMethod(models.TextChoices):
    CASH = 'Cash', 'Cash (USD)'
    ECOCASH = 'EcoCash', 'EcoCash'
    SWIPE = 'Swipe', 'Swipe / POS Card'
    BANK_TRANSFER = 'Bank Transfer', 'Bank Transfer / ZIPIT'
    INNBUCKS = 'InnBucks', 'InnBucks'
    MUKURU = 'Mukuru', 'Mukuru'


class Sale(models.Model):
    """
    Sales header.
    Transaction date is captured automatically at DB level (auto_now_add=True).
    Contains multiple items via SaleItem.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='sales'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue of this transaction"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total cost of goods sold via FIFO"
    )
    total_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total profit (Amount - Cost)"
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    date_sold = models.DateField(
        auto_now_add=True,
        db_index=True,
        help_text="Automatically captured transaction date"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_sales',
        help_text="Cashier/staff who processed the sale"
    )
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            date_prefix = timezone.now().strftime('%Y%m%d')
            unique_suffix = uuid.uuid4().hex[:6].upper()
            self.invoice_number = f"INV-{date_prefix}-{unique_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} — {self.customer.name} (${self.total_amount})"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class SaleItem(models.Model):
    """
    Line item in a sale transaction.
    Serial number is optional per item. If entered, quantity is strictly 1.
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='sale_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Selling price per unit (USD)"
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Line total (unit_price * quantity)"
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total cost deducted via FIFO"
    )
    profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Profit on this line item"
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Optional serial number for 1:1 serialized item"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (${self.total_price})"


class SaleBatchDeduction(models.Model):
    """
    FIFO audit trail: records exact batch deductions for each sale item.
    """
    sale_item = models.ForeignKey(
        SaleItem,
        on_delete=models.CASCADE,
        related_name='batch_deductions'
    )
    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name='sale_deductions'
    )
    quantity_deducted = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sale Batch Deduction'
        verbose_name_plural = 'Sale Batch Deductions'
