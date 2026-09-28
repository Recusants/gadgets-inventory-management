from django.db import models

class CompanySetting(models.Model):
    company_name = models.CharField(max_length=200, default="21 Void Technologies")
    tagline = models.CharField(max_length=250, default="Fusing Technology With Market Intelligence")
    phone = models.CharField(max_length=50, default="+263 77 123 4567")
    email = models.EmailField(default="info@21void.com")
    address = models.TextField(default="Harare, Zimbabwe")
    currency_symbol = models.CharField(max_length=10, default="$")
    currency_code = models.CharField(max_length=10, default="USD")
    receipt_header_note = models.CharField(max_length=250, default="Official Purchase Receipt")
    receipt_footer_note = models.TextField(default="Thank you for doing business with 21 Void Technologies! All products guaranteed authentic.")
    logo = models.ImageField(upload_to='company/', null=True, blank=True, help_text="Custom Company Logo for Receipts and Header")
    is_customized = models.BooleanField(default=False, help_text="Flag indicating company profile has been configured")
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = 'Company Setting'
        verbose_name_plural = 'Company Settings'

    def __str__(self):
        return self.company_name

    @classmethod
    def get_settings(cls):
        settings_obj, _ = cls.objects.get_or_create(id=1)
        return settings_obj


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LOW_STOCK = 'LOW_STOCK', 'Low Stock Alert'
        EXPIRING = 'EXPIRING', 'Expiry Alert'
        SYSTEM = 'SYSTEM', 'System Notice'
        EXPENSE = 'EXPENSE', 'Expense Notice'

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.LOW_STOCK)
    product = models.ForeignKey(
        'inventory.Product',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications'
    )
    batch = models.ForeignKey(
        'inventory.StockBatch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications'
    )
    severity = models.CharField(
        max_length=20,
        default='WARNING',
        choices=[
            ('INFO', 'Informational'),
            ('WARNING', 'Warning / Reorder'),
            ('URGENT', 'Urgent Attention'),
            ('CRITICAL', 'Critical / Out of Stock'),
        ]
    )
    is_read = models.BooleanField(default=False, db_index=True)
    link_url = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

    @property
    def stock_level_data(self):
        """
        Calculates exact stock remaining relative to the reorder level.
        Returns detailed color-coding data for badges, gauges, and bars.
        """
        if self.notification_type != self.NotificationType.LOW_STOCK or not self.product:
            return None

        try:
            stock = self.product.stock
            qty = max(0, stock.quantity_available)
            reorder = max(1, stock.reorder_quantity)
            ratio = qty / reorder
            pct = min(100, max(0, round(ratio * 100)))

            if qty == 0:
                color = 'red'
                badge_bg = 'bg-red-500 text-white'
                badge_soft = 'bg-red-100 text-red-700 border-red-200'
                bar_bg = 'bg-red-500'
                label = 'Depleted (0%)'
                level = 'OUT_OF_STOCK'
            elif pct <= 25:
                color = 'rose'
                badge_bg = 'bg-rose-600 text-white'
                badge_soft = 'bg-rose-100 text-rose-800 border-rose-200'
                bar_bg = 'bg-rose-500'
                label = f'Critical ({pct}%)'
                level = 'CRITICAL'
            elif pct <= 50:
                color = 'orange'
                badge_bg = 'bg-orange-600 text-white'
                badge_soft = 'bg-orange-100 text-orange-800 border-orange-200'
                bar_bg = 'bg-orange-500'
                label = f'Urgent ({pct}%)'
                level = 'URGENT'
            elif pct <= 75:
                color = 'amber'
                badge_bg = 'bg-amber-600 text-white'
                badge_soft = 'bg-amber-100 text-amber-800 border-amber-200'
                bar_bg = 'bg-amber-500'
                label = f'Low ({pct}%)'
                level = 'LOW'
            else:
                color = 'yellow'
                badge_bg = 'bg-yellow-600 text-white'
                badge_soft = 'bg-yellow-100 text-yellow-800 border-yellow-200'
                bar_bg = 'bg-yellow-500'
                label = f'Reorder ({pct}%)'
                level = 'REORDER'

            return {
                'qty': qty,
                'reorder': reorder,
                'pct': pct,
                'color': color,
                'badge_bg': badge_bg,
                'badge_soft': badge_soft,
                'bar_bg': bar_bg,
                'label': label,
                'level': level,
            }
        except Exception:
            return None

    @property
    def expiry_data(self):
        """
        Calculates expiry status for EXPIRING notifications.
        Returns visual badges, color-coding, and days remaining.
        """
        if self.notification_type != self.NotificationType.EXPIRING:
            return None

        from django.utils import timezone
        today = timezone.now().date()
        exp_date = None
        days = None

        if self.batch and self.batch.expiration_date:
            exp_date = self.batch.expiration_date
            days = (exp_date - today).days

        if days is None:
            return None

        if days < 0:
            return {
                'days': days,
                'abs_days': abs(days),
                'exp_date': exp_date,
                'color': 'red',
                'badge_bg': 'bg-red-500 text-white',
                'badge_soft': 'bg-red-100 text-red-700 border-red-200',
                'label': f'Expired ({abs(days)}d ago)',
                'level': 'EXPIRED'
            }
        elif days <= 7:
            return {
                'days': days,
                'abs_days': days,
                'exp_date': exp_date,
                'color': 'rose',
                'badge_bg': 'bg-rose-600 text-white',
                'badge_soft': 'bg-rose-100 text-rose-800 border-rose-200',
                'label': f'Expires in {days}d',
                'level': 'CRITICAL'
            }
        elif days <= 30:
            return {
                'days': days,
                'abs_days': days,
                'exp_date': exp_date,
                'color': 'orange',
                'badge_bg': 'bg-orange-600 text-white',
                'badge_soft': 'bg-orange-100 text-orange-800 border-orange-200',
                'label': f'{days} days left',
                'level': 'URGENT'
            }
        else:
            return {
                'days': days,
                'abs_days': days,
                'exp_date': exp_date,
                'color': 'amber',
                'badge_bg': 'bg-amber-600 text-white',
                'badge_soft': 'bg-amber-100 text-amber-800 border-amber-200',
                'label': f'{days} days left',
                'level': 'WARNING'
            }

