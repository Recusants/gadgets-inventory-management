# fiscalisation/models.py
from django.db import models
from django.utils import timezone
from decimal import Decimal


class FiscalisationSettings(models.Model):
    """Global settings for fiscalisation"""
    
    fiscalisation_enabled = models.BooleanField(default=False)
    paused_at = models.DateTimeField(null=True, blank=True)
    paused_by = models.CharField(max_length=100, blank=True)
    pause_reason = models.TextField(blank=True)
    allowed_currences = models.CharField(max_length=200, default="USD, ZWG")
    
    # Binary API Settings
    api_base_url = models.CharField(max_length=200, default="https://Zimratest.samcima.com/api/Zimra")
    qr_url = models.CharField(max_length=200, default="https://fdmstest.zimra.co.zw", help_text="QR URL from ZIMRA getConfig")
    device_id = models.CharField(max_length=50, blank=True, help_text="Your ZIMRA Device ID")
    machine_code = models.CharField(max_length=50, blank=True, help_text="Machine code provided by Binary Software")
    api_password = models.CharField(max_length=100, blank=True, help_text="Password provided by Binary Software")
    default_hs_code = models.CharField(max_length=30, default="95069100", blank=True, verbose_name="Default ZIMRA HS Code", help_text="Fallback / last-resort HS Code used during ZIMRA fiscalisation")
    
    # Sync settings
    sync_interval_seconds = models.IntegerField(default=30)
    max_retry_count = models.IntegerField(default=5)
    retry_delay_seconds = models.IntegerField(default=60)
    
    auto_resume_on_success = models.BooleanField(default=True)
    
    admin_email = models.EmailField(blank=True)
    admin_phone = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fiscalisation Settings"
        verbose_name_plural = "Fiscalisation Settings"
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def is_fiscalisation_active(self):
        return self.fiscalisation_enabled
    
    def pause(self, reason="", user=""):
        self.fiscalisation_enabled = False
        self.paused_at = timezone.now()
        self.paused_by = user
        self.pause_reason = reason
        self.save()
    
    def resume(self):
        self.fiscalisation_enabled = True
        self.paused_at = None
        self.paused_by = ""
        self.pause_reason = ""
        self.save()
    
    def __str__(self):
        return f"Fiscalisation Settings (Active: {self.fiscalisation_enabled})"


class FiscalReceiptSequence(models.Model):
    fiscal_receipt_number = models.IntegerField(default=0)
    fiscal_receipt_global_no = models.IntegerField(default=0)
    last_fiscal_day = models.DateField(null=True, blank=True)

    
    class Meta:
        verbose_name = "Fiscal Receipt Sequence"
        verbose_name_plural = "Fiscal Receipt Sequences"
    
    @classmethod
    def get_next_number(cls):
        sequence, created = cls.objects.get_or_create(id=1)
        today = timezone.now().date()
        
        if sequence.last_fiscal_day != today:
            sequence.fiscal_receipt_number = 0
            sequence.last_fiscal_day = today
        
        sequence.fiscal_receipt_number += 1
        sequence.fiscal_receipt_global_no += 1
        sequence.save()
        
        return {
            'daily': sequence.fiscal_receipt_number,
            'global': sequence.fiscal_receipt_global_no
        }
    
    def __str__(self):
        return f"Sequence: Daily #{self.fiscal_receipt_number}, Global #{self.fiscal_receipt_global_no}"


class FiscalReceipt(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_SYNCED = 'SYNCED'
    STATUS_FAILED = 'FAILED'
    STATUS_BYPASSED = 'BYPASSED'
    STATUS_VOID = 'VOID'
    STATUS_PROCESSING = 'PROCESSING'  # Make sure this exists
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Sync'),
        (STATUS_PROCESSING, 'Processing...'),
        (STATUS_SYNCED, 'Synced to ZIMRA'),
        (STATUS_FAILED, 'Failed - Needs Retry'),
        (STATUS_BYPASSED, 'Bypassed - Fiscalisation was off'),
        (STATUS_VOID, 'Voided'),
    ]
    
    TYPE_INVOICE = 'FISCALINVOICE'
    TYPE_CREDIT_NOTE = 'CREDITNOTE'
    TYPE_DEBIT_NOTE = 'DEBITNOTE'
    
    TYPE_CHOICES = [
        (TYPE_INVOICE, 'Fiscal Invoice'),
        (TYPE_CREDIT_NOTE, 'Credit Note'),
        (TYPE_DEBIT_NOTE, 'Debit Note'),
    ]

    the_password = models.CharField(max_length=60, null=True, blank=True)
    role = models.CharField(max_length=15, null=True, blank=True)
    payment_lines = models.JSONField(default=list, blank=True, help_text="List of payment methods and amounts")
    line_items = models.JSONField(default=list)
    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    inv_number = models.IntegerField(null=True, blank=True)
    inv_number_global = models.IntegerField(null=True, blank=True)
    doc_currency = models.CharField(max_length=3, default="USD")
    my_yyy_mm_dd_date = models.DateField()
    my_24hr_time_format_with_seconds = models.CharField(max_length=20)
    document_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nontaxible_sales_amt_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    zero_per_taxamt = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    zero_perc_sales_amt_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amt_15_perc = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_15_perc_sales_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    machinecode = models.CharField(max_length=10, default="")
    the_password = models.CharField(max_length=10, default="")
    invoice_number_to_credit_debit = models.IntegerField(null=True, blank=True)
    buyer_register_name = models.CharField(max_length=50, null=True, blank=True, default="")
    buyer_TIN = models.CharField(max_length=15, null=True, blank=True, default="")
    VAT_number = models.CharField(max_length=15, null=True, blank=True, default="")
    phone_no = models.CharField(max_length=50, null=True, blank=True, default="")
    email = models.CharField(max_length=50, null=True, blank=True, default="")

    local_receipt_number = models.IntegerField(null=True, blank=True)  #This is the reciept number rafrence to the model SaleTransaction
    local_invoice_number_to_credit_debit = models.IntegerField(null=True, blank=True) #This is the Credit note number rafrence to the model CreditNote

    binary_server_response = models.JSONField(default=dict, blank=True)
    qr_code_url = models.URLField(max_length=500, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    retry_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)
    last_sync_attempt = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(null=True, blank=True)
        
    # # ========== Link to your existing system ==========
    # internal_sale_id = models.IntegerField(null=True, blank=True)
    # internal_invoice_id = models.IntegerField(null=True, blank=True)
    # internal_invoice_number = models.CharField(max_length=50)
    
    # # ========== Fiscal receipt own sequence ==========
    # fiscal_receipt_number = models.IntegerField(null=True, blank=True)
    # fiscal_receipt_global_no = models.IntegerField(null=True, blank=True)
    
    # # ========== Receipt Data ==========
    # receipt_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INVOICE)
    # currency = models.CharField(max_length=3, default="USD")
    # transaction_date = models.DateField()
    # transaction_time = models.CharField(max_length=20)
    # subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    # tax_breakdown = models.JSONField(default=dict)
    
    # # Payment details
    # payment_method = models.CharField(max_length=50, default="Cash")
    # payment_amount = models.DecimalField(max_digits=15, decimal_places=2)
    # payments = models.JSONField(default=list, blank=True, help_text="List of payment methods and amounts")
    
    # # Buyer information
    # buyer_name = models.CharField(max_length=250, blank=True)
    # buyer_tin = models.CharField(max_length=50, blank=True)
    # buyer_vat = models.CharField(max_length=50, blank=True)
    # buyer_address = models.TextField(blank=True)
    # buyer_phone = models.CharField(max_length=50, blank=True)
    # buyer_email = models.EmailField(blank=True)
    
    # # For credit/debit notes
    # original_fiscal_receipt = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_notes')
    # original_invoice_number = models.CharField(max_length=50, blank=True)
    
    # # Line Items
    # line_items = models.JSONField(default=list)
    
    # # Binary API Response
    # binary_response = models.JSONField(default=dict, blank=True)
    # qr_code_url = models.URLField(max_length=500, blank=True)
    
    # # Status Tracking
    # status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # retry_count = models.IntegerField(default=0)
    # last_error = models.TextField(blank=True)
    # last_sync_attempt = models.DateTimeField(null=True, blank=True)

    # # Add to FiscalReceipt model:
    # device_signature_hash = models.TextField(blank=True, null=True)
    # device_signature = models.TextField(blank=True, null=True)
    
    # # Timestamps
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    # synced_at = models.DateTimeField(null=True, blank=True)
    
    # class Meta:
    #     ordering = ['-created_at']
    #     indexes = [
    #         models.Index(fields=['status', 'retry_count']),
    #         models.Index(fields=['internal_invoice_number']),
    #         models.Index(fields=['fiscal_receipt_number']),
    #         models.Index(fields=['created_at']),
    #         models.Index(fields=['status']),
    #     ]
    
    def __str__(self):
        return f"[{ str(self.created_at)[:16] }] Fiscal #{self.inv_number or '?'} - Internal: {self.local_receipt_number} - {self.status} ---- {self.doc_type} --- { self.qr_code_url}"
    
    @property
    def display_receipt_number(self):
        if self.inv_number:
            return str(self.inv_number).zfill(10)
        return "PENDING"
    

    def mark_processing(self):
        """Mark receipt as being processed"""
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_synced(self, qr_url, response_data):
        self.status = self.STATUS_SYNCED
        self.qr_code_url = qr_url
        self.binary_server_response = response_data
        self.synced_at = timezone.now()
        self.last_error = ""
        self.save()
    
    def mark_failed(self, error_message):
        self.status = self.STATUS_FAILED
        self.retry_count += 1
        self.last_error = error_message
        self.last_sync_attempt = timezone.now()
        self.save()
    
    def mark_pending(self):
        self.status = self.STATUS_PENDING
        self.save()
    
    def mark_bypassed(self):
        self.status = self.STATUS_BYPASSED
        self.save()
    
    def can_retry(self):
        return self.status in [self.STATUS_FAILED, self.STATUS_PENDING] and self.retry_count < 5
    
    def get_payments_list(self):
        if isinstance(self.payments, list):
            return self.payments
        return []
    
    def get_total_paid(self):
        total = sum(p.get('amount', 0) for p in self.get_payments_list())
        return Decimal(str(total))


class SyncQueue(models.Model):
    fiscal_receipt = models.ForeignKey(FiscalReceipt, on_delete=models.CASCADE)
    priority = models.IntegerField(default=0)
    scheduled_for = models.DateTimeField(default=timezone.now)
    attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-priority', 'scheduled_for']
        indexes = [models.Index(fields=['scheduled_for', 'locked_until'])]
    
    def __str__(self):
        return f"Queue: Receipt #{self.fiscal_receipt_id} - Priority {self.priority}"


class SyncLog(models.Model):
    fiscal_receipt = models.ForeignKey(FiscalReceipt, on_delete=models.CASCADE, null=True, blank=True)
    attempt_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    synced_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-attempt_time']
        indexes = [models.Index(fields=['attempt_time'])]
    
    def __str__(self):
        return f"Sync at {self.attempt_time}: {self.synced_count} synced, {self.failed_count} failed"