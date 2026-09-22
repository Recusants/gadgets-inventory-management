from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    default_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Default expense amount"
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this expense category auto-recurs periodically"
    )
    recurring_interval = models.CharField(
        max_length=20,
        default='MONTHLY',
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('YEARLY', 'Yearly'),
        ],
        help_text="Recurring frequency interval"
    )
    last_recurring_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date an automatic recurring expense was recorded"
    )

    class Meta:
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_spent(self):
        total = self.expenses.aggregate(models.Sum('amount'))['amount__sum']
        return total or Decimal('0.00')

    @property
    def expense_count(self):
        return self.expenses.count()


class Expense(models.Model):
    title = models.CharField(max_length=200, help_text="Description or purpose of the expense")
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount spent (USD)"
    )
    date = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Date when expense was incurred"
    )
    payment_method = models.CharField(
        max_length=30,
        default='Cash',
        choices=[
            ('Cash', 'Cash (USD)'),
            ('EcoCash', 'EcoCash'),
            ('Swipe', 'Swipe / POS Card'),
            ('Bank Transfer', 'Bank Transfer / ZIPIT'),
            ('InnBucks', 'InnBucks'),
            ('Mukuru', 'Mukuru'),
            ('Other', 'Other')
        ]
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Receipt, voucher or reference number"
    )
    notes = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} — ${self.amount} ({self.date})"
