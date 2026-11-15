from django.contrib import admin
from .models import FiscalisationSettings, FiscalReceiptSequence, FiscalReceipt, SyncQueue, SyncLog


@admin.register(FiscalisationSettings)
class FiscalisationSettingsAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'machine_code', 'fiscalisation_enabled', 'api_base_url', 'default_hs_code', 'sync_interval_seconds', 'paused_at')
    list_editable = ('fiscalisation_enabled',)


@admin.register(FiscalReceiptSequence)
class FiscalReceiptSequenceAdmin(admin.ModelAdmin):
    list_display = ('fiscal_receipt_number', 'fiscal_receipt_global_no', 'last_fiscal_day')


@admin.register(FiscalReceipt)
class FiscalReceiptAdmin(admin.ModelAdmin):
    list_display = ('inv_number', 'inv_number_global', 'doc_type', 'doc_currency', 'document_total', 'status', 'retry_count', 'local_receipt_number', 'buyer_register_name', 'created_at')
    list_filter = ('doc_type', 'status', 'doc_currency', 'created_at')
    search_fields = ('inv_number', 'inv_number_global', 'local_receipt_number', 'buyer_register_name', 'buyer_TIN')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'synced_at')


@admin.register(SyncQueue)
class SyncQueueAdmin(admin.ModelAdmin):
    list_display = ('fiscal_receipt', 'priority', 'scheduled_for', 'attempts', 'locked_until')
    list_filter = ('priority',)
    search_fields = ('fiscal_receipt__inv_number', 'error_message')


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('attempt_time', 'success', 'synced_count', 'failed_count', 'response_code', 'duration_ms', 'fiscal_receipt')
    list_filter = ('success', 'attempt_time')
    search_fields = ('fiscal_receipt__inv_number', 'response_body', 'error_message')
    date_hierarchy = 'attempt_time'
