# fiscalisation/services.py
import json
import requests
import logging
import threading
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, List
from django.utils import timezone
from django.db import transaction

from .models import FiscalisationSettings, FiscalReceipt, FiscalReceiptSequence, SyncLog

logger = logging.getLogger(__name__)


# ============================================================
# RECEIPT CREATION
# ============================================================

@transaction.atomic
def create_fiscal_receipt(
    the_password,
    role,
    payment_lines,
    line_items,
    doc_type,
    doc_currency,
    my_yyy_mm_dd_date,
    my_24hr_time_format_with_seconds,
    document_total,
    nontaxible_sales_amt_total,
    zero_per_taxamt,
    zero_perc_sales_amt_total,
    tax_amt_15_perc,
    tax_15_perc_sales_total,
    invoice_number_to_credit_debit,
    local_invoice_number_to_credit_debit,
    buyer_register_name,
    buyer_TIN,
    VAT_number,
    phone_no,
    email,
    local_receipt_number,
    status
):
    """Create a fiscal receipt with atomic transaction"""
    
    sequence = FiscalReceiptSequence.objects.select_for_update().first()
    if not sequence:
        sequence = FiscalReceiptSequence.objects.create(id=1)
    
    next_numbers = sequence.get_next_number()

    new_fiscal_receipt = FiscalReceipt(
        the_password=the_password,
        role=role,
        payment_lines=payment_lines,
        line_items=line_items,
        doc_type=doc_type,
        inv_number=next_numbers['global'],
        doc_currency=doc_currency,
        my_yyy_mm_dd_date=my_yyy_mm_dd_date,
        my_24hr_time_format_with_seconds=my_24hr_time_format_with_seconds,
        document_total=document_total,
        nontaxible_sales_amt_total=nontaxible_sales_amt_total,
        zero_per_taxamt=zero_per_taxamt,
        zero_perc_sales_amt_total=zero_perc_sales_amt_total,
        tax_amt_15_perc=tax_amt_15_perc,
        tax_15_perc_sales_total=tax_15_perc_sales_total,
        invoice_number_to_credit_debit=invoice_number_to_credit_debit,
        local_invoice_number_to_credit_debit=local_invoice_number_to_credit_debit,
        buyer_register_name=buyer_register_name,
        buyer_TIN=buyer_TIN,
        VAT_number=VAT_number,
        phone_no=phone_no,
        email=email,
        local_receipt_number=local_receipt_number,
        status=status
    )
    new_fiscal_receipt.save()
    
    return new_fiscal_receipt


# ============================================================
# API CLIENT
# ============================================================

def make_request(method, endpoint, params=None, data=None):
    """Make HTTP request to Binary API"""
    settings = FiscalisationSettings.get_settings()
    
    base_url = settings.api_base_url.rstrip('/')
    
    if endpoint.startswith('/'):
        url = f"{base_url}{endpoint}"
    else:
        url = f"{base_url}/{endpoint}"
    
    print(f"\n{'='*80}")
    print(f"API REQUEST: {method} {url}")
    print(f"{'='*80}")
    
    if data:
        print(f"\n📤 PAYLOAD BEING SENT:")
        print(json.dumps(data, indent=2))
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, timeout=30, verify=True)
        else:
            response = requests.post(url, params=params, json=data, timeout=30, verify=True)
        
        print(f"\n📥 RESPONSE:")
        print(f"  Status Code: {response.status_code}")
        
        response_text = response.text.strip()
        print(f"  Response: {response_text[:500]}")
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                if isinstance(json_response, dict):
                    # Look for QR URL in response
                    qr_fields = ['qrCodeUrl', 'qr_code', 'qrUrl', 'qrURL', 'url', 'qr']
                    for field in qr_fields:
                        if field in json_response and json_response[field] and str(json_response[field]).startswith('http'):
                            return json_response[field]
                    # Check if response contains a QR URL in any string value
                    for key, value in json_response.items():
                        if isinstance(value, str) and value.startswith('http') and ('zimra' in value or 'receipt' in value):
                            return value
                return json_response
            except:
                if response_text.startswith('http'):
                    return response_text
                return response_text
        else:
            try:
                return response.json()
            except:
                return {'error': response_text, 'status_code': response.status_code}
                
    except requests.exceptions.SSLError as e:
        print(f"  ❌ SSL ERROR: {e}")
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30, verify=False)
            else:
                response = requests.post(url, params=params, json=data, timeout=30, verify=False)
            
            if response.status_code == 200:
                return response.text
            else:
                return {'error': response.text, 'status_code': response.status_code}
        except Exception as e2:
            return {'error': str(e2)}
    except Exception as e:
        print(f"  ❌ REQUEST ERROR: {e}")
        return {'error': str(e)}


def get_device_status():
    """Get device status from Binary API"""
    settings = FiscalisationSettings.get_settings()
    return make_request('GET', '/GetZimraStatus', params={"DeviceID": settings.device_id})


def get_config_tax():
    """Get tax configuration from Binary API"""
    settings = FiscalisationSettings.get_settings()
    return make_request('GET', '/GetConfigTax', params={"DeviceID": settings.device_id})


def submit_invoice(payload):
    """Submit invoice to Binary API"""
    return make_request('POST', '/ThePost', data=payload)


# ============================================================
# SYNC FUNCTIONS
# ============================================================

def sync_receipt_sync(fiscal_receipt_id):
    """Sync a single receipt to ZIMRA (synchronous version)"""
    try:
        fiscal_receipt = FiscalReceipt.objects.get(id=fiscal_receipt_id)
    except FiscalReceipt.DoesNotExist:
        logger.error(f"Receipt {fiscal_receipt_id} not found")
        return False
    
    fiscal_device = FiscalisationSettings.objects.first()
    
    # Mark as processing
    fiscal_receipt.mark_processing()

    # Build payment line
    payment_line = fiscal_receipt.payment_lines if isinstance(fiscal_receipt.payment_lines, list) else []
    
    # Build receipt details
    receipt_details = fiscal_receipt.line_items if isinstance(fiscal_receipt.line_items, list) else []

    # Build header - CRITICAL: Must be an array with one object
    header = [{
        "DocType": fiscal_receipt.doc_type,
        "DeviceId": fiscal_device.device_id,
        "InvNumber": str(fiscal_receipt.inv_number),
        "DocCurrency": fiscal_receipt.doc_currency,
        "myYYY_MM_DDdate": str(fiscal_receipt.my_yyy_mm_dd_date),
        "My24hrTimeformatwithSeconds": str(fiscal_receipt.my_24hr_time_format_with_seconds),
        "DocumentTotal": f"{float(fiscal_receipt.document_total):.2f}",
        "nontaxible_salesAmtTotal": f"{float(fiscal_receipt.nontaxible_sales_amt_total):.2f}",
        "ZeroPer_Taxamt": f"{float(fiscal_receipt.zero_per_taxamt):.2f}",
        "ZeroPerc_SalesAmtTotal": f"{float(fiscal_receipt.zero_perc_sales_amt_total):.2f}",
        "TaxAmt15Perc": f"{float(fiscal_receipt.tax_amt_15_perc):.2f}",
        "Tax15Perc_SalesTotal": f"{float(fiscal_receipt.tax_15_perc_sales_total):.2f}",
        "machinecode": fiscal_device.machine_code,
        "ThePassword": fiscal_device.api_password,
        "InvoicenumbertoCredit_debit": str(fiscal_receipt.invoice_number_to_credit_debit or "0"),
        "buyerRegisterName": fiscal_receipt.buyer_register_name or "",
        "buyerTIN": fiscal_receipt.buyer_TIN or "",
        "VATNumber": fiscal_receipt.VAT_number or "",
        "phoneNo": fiscal_receipt.phone_no or "",
        "email": fiscal_receipt.email or "",
    }]

    # Build complete payload
    payload = {
        "id": 0,
        "ThePassword": None,
        "Role": None,
        "paymentline": payment_line,
        "ReceiptDetail": receipt_details,
        "TheHeader": header
    }

    print(f"\n📤 Syncing Receipt #{fiscal_receipt.inv_number}")
    print(json.dumps(payload, indent=2))
    
    # Submit to API
    response = submit_invoice(payload)

    # Process response
    if isinstance(response, str):
        if response.startswith('http'):
            fiscal_receipt.mark_synced(response, {'qr_url': response})
            print(f"✅ SUCCESS! Receipt #{fiscal_receipt.inv_number} synced")
            return True
        else:
            fiscal_receipt.mark_failed(response)
            print(f"❌ FAILED! Receipt #{fiscal_receipt.inv_number}: {response}")
            return False
    
    elif isinstance(response, dict):
        # Check for success indicators
        if response.get('success') is True:
            qr_url = None
            for key in ['qrCodeUrl', 'qr_code', 'qrUrl', 'qrURL', 'url']:
                if key in response and response[key] and str(response[key]).startswith('http'):
                    qr_url = response[key]
                    break
            
            if not qr_url:
                for key, value in response.items():
                    if isinstance(value, str) and value.startswith('http') and ('zimra' in value or 'receipt' in value):
                        qr_url = value
                        break
            
            if qr_url:
                fiscal_receipt.mark_synced(qr_url, response)
                print(f"✅ SUCCESS! Receipt #{fiscal_receipt.inv_number} synced")
                return True
        
        # Error case
        error_msg = response.get('error') or response.get('title') or response.get('message') or str(response)
        fiscal_receipt.mark_failed(error_msg)
        print(f"❌ FAILED! Receipt #{fiscal_receipt.inv_number}: {error_msg}")
        return False
    
    fiscal_receipt.mark_failed(f"Unexpected response: {response}")
    return False


def sync_receipt(fiscal_receipt_id):
    """Sync receipt with logging"""
    log = SyncLog.objects.create(
        fiscal_receipt_id=fiscal_receipt_id,
        success=False
    )
    
    start_time = timezone.now()
    
    try:
        success = sync_receipt_sync(fiscal_receipt_id)
        log.success = success
        if success:
            log.synced_count = 1
        else:
            log.failed_count = 1
    except Exception as e:
        log.error_message = str(e)
        log.failed_count = 1
        logger.exception(f"Sync error for receipt {fiscal_receipt_id}")
    finally:
        log.duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        log.save()
    
    return log.success


# ============================================================
# IMPORTANT: ADD THIS FUNCTION - This is what was missing!
# ============================================================

def sync_receipt_async(fiscal_receipt_id):
    """Sync receipt in a background thread - non-blocking"""
    def sync_task():
        try:
            sync_receipt(fiscal_receipt_id)
        except Exception as e:
            logger.exception(f"Background sync failed for receipt {fiscal_receipt_id}")
    
    thread = threading.Thread(target=sync_task, daemon=True)
    thread.start()
    return thread


# ============================================================
# BULK SYNC FUNCTIONS
# ============================================================

@transaction.atomic
def sync_pending_receipts(limit=100, async_mode=True):
    """Sync all pending receipts (atomic)"""
    settings = FiscalisationSettings.get_settings()
    
    pending = FiscalReceipt.objects.select_for_update().filter(
        status__in=[FiscalReceipt.STATUS_PENDING],# FiscalReceipt.STATUS_FAILED],
        retry_count__lt=settings.max_retry_count
    ).order_by('created_at')[:limit]
    
    results = {'success': 0, 'failed': 0, 'total': pending.count()}
    
    if async_mode:
        threads = []
        for receipt in pending:
            receipt.mark_processing()
            thread = threading.Thread(
                target=sync_receipt,
                args=(receipt.id,),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        return {
            'total': results['total'],
            'started': len(threads),
            'mode': 'async'
        }
    else:
        for receipt in pending:
            if sync_receipt_sync(receipt.id):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results


@transaction.atomic
def retry_failed_receipts(limit=50, async_mode=True):
    """Reset and retry failed receipts (atomic)"""
    failed = FiscalReceipt.objects.select_for_update().filter(
        status=FiscalReceipt.STATUS_FAILED,
        retry_count__lt=FiscalisationSettings.get_settings().max_retry_count
    ).order_by('created_at')[:limit]
    
    results = {'reset': 0, 'total': failed.count()}
    
    for receipt in failed:
        receipt.mark_pending()
        results['reset'] += 1
    
    if results['reset'] > 0:
        if async_mode:
            threading.Thread(
                target=sync_pending_receipts,
                args=(results['reset'], True),
                daemon=True
            ).start()
        else:
            sync_pending_receipts(results['reset'], False)
    
    return results


# ============================================================
# STATISTICS
# ============================================================

def get_fiscal_dashboard_stats():
    """Get dashboard statistics"""
    return {
        'total': FiscalReceipt.objects.count(),
        'synced': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_SYNCED).count(),
        'pending': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_PENDING).count(),
        'processing': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_PROCESSING).count(),
        'failed': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_FAILED).count(),
        'bypassed': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_BYPASSED).count(),
        'void': FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_VOID).count(),
    }