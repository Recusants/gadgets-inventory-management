# fiscalisation/urls.py
from django.urls import path
from . import views

app_name = 'fiscalisation'

urlpatterns = [
    # Main SPA view
    path('', views.dashboard_spa, name='dashboard'),
    
    # API endpoints
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/receipts/', views.api_receipts, name='api_receipts'),
    path('api/receipt/<int:receipt_id>/', views.api_receipt_detail, name='api_receipt_detail'),
    path('api/receipt/<int:receipt_id>/', views.api_update_receipt, name='api_update_receipt'),
    path('api/sync/<int:receipt_id>/', views.api_sync_receipt, name='api_sync_receipt'),
    path('api/sync-all/', views.api_sync_all, name='api_sync_all'),
    path('api/retry-failed/', views.api_retry_failed, name='api_retry_failed'),
    path('api/toggle/', views.api_toggle_fiscalisation, name='api_toggle'),
    path('api/bulk-action/', views.api_bulk_action, name='api_bulk_action'),
    path('api/test-connection/', views.api_test_connection, name='api_test_connection'),
    path('api/tax-config/', views.api_tax_config, name='api_tax_config'),
    path('api/void/<int:receipt_id>/', views.api_void_receipt, name='api_void_receipt'),
    path('api/settings/', views.api_settings, name='api_settings'),
    path('api/logs/', views.api_logs, name='api_logs'),
    
    # Tax Report endpoints
    path('api/tax-report/', views.api_tax_report, name='api_tax_report'),
    path('api/tax-report-summary/', views.api_tax_report_summary, name='api_tax_report_summary'),
    path('api/tax-report-export/', views.api_tax_report_export, name='api_tax_report_export'),
]