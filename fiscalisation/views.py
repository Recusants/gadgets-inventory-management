# fiscalisation/views.py
import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from datetime import datetime
from django.utils import timezone

from decimal import Decimal

from .models import FiscalisationSettings, FiscalReceipt, SyncLog
from .services import (
    sync_receipt_async, sync_pending_receipts, retry_failed_receipts,
    get_device_status, get_config_tax, get_fiscal_dashboard_stats,
    sync_receipt_sync, make_request
)

logger = logging.getLogger(__name__)


@login_required
def dashboard_spa(request):
    """Single-page dashboard for fiscalisation management"""
    settings_obj = FiscalisationSettings.get_settings()
    
    context = {
        'fiscalisation_active': settings_obj.is_fiscalisation_active(),
        'settings': settings_obj,
        'device_id': settings_obj.device_id,
        'api_base_url': settings_obj.api_base_url,
        'machine_code': settings_obj.machine_code,
    }
    return render(request, 'fiscalisation/dashboard_spa.html', context)


# ============================================================
# API ENDPOINTS
# ============================================================


@login_required
def api_tax_report(request):
    """
    Generate tax report with breakdown by tax rate, currency, and payment method.
    Shows sales value under every tax code with currency and method combinations.
    """
    try:
        # Get filters from request
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        currency = request.GET.get('currency')
        status = request.GET.get('status', 'SYNCED')
        
        # Build query
        receipts = FiscalReceipt.objects.all()
        
        # Filter by status (default to SYNCED)
        if status:
            receipts = receipts.filter(status=status)
        else:
            receipts = receipts.filter(status=FiscalReceipt.STATUS_SYNCED)
        
        # Filter by date range
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                receipts = receipts.filter(my_yyy_mm_dd_date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                receipts = receipts.filter(my_yyy_mm_dd_date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Filter by currency
        if currency:
            receipts = receipts.filter(doc_currency=currency.upper())
        
        # Calculate tax breakdown with payment methods
        tax_breakdown = {}
        payment_methods = {}
        total_sales = Decimal('0')
        total_tax = Decimal('0')
        total_receipts = receipts.count()
        currency_used = currency or 'ALL'
        
        for receipt in receipts:
            # Get sales amounts
            sales_15 = Decimal(str(receipt.tax_15_perc_sales_total or 0))
            sales_0 = Decimal(str(receipt.zero_perc_sales_amt_total or 0))
            sales_exempt = Decimal(str(receipt.nontaxible_sales_amt_total or 0))
            tax_15 = Decimal(str(receipt.tax_amt_15_perc or 0))
            
            receipt_total = sales_15 + sales_0 + sales_exempt
            total_sales += receipt_total
            total_tax += tax_15
            
            # Get payment methods from receipt
            payment_methods_list = receipt.payment_lines if receipt.payment_lines else []
            receipt_currency = receipt.doc_currency or 'USD'
            
            # Track payment methods for this receipt
            for payment in payment_methods_list:
                method_name = payment.get('PaymentMethodName', 'OTHER').upper()
                amount = Decimal(str(payment.get('PaymentAmt', 0)))
                
                # Build key: currency + method
                method_key = f"{receipt_currency}_{method_name}"
                
                if method_key not in payment_methods:
                    payment_methods[method_key] = {
                        'currency': receipt_currency,
                        'method': method_name,
                        'total': Decimal('0'),
                        'count': 0,
                    }
                payment_methods[method_key]['total'] += amount
                payment_methods[method_key]['count'] += 1
            
            # If no payment lines, use default
            if not payment_methods_list:
                method_key = f"{receipt_currency}_CASH"
                if method_key not in payment_methods:
                    payment_methods[method_key] = {
                        'currency': receipt_currency,
                        'method': 'CASH',
                        'total': Decimal('0'),
                        'count': 0,
                    }
                payment_methods[method_key]['total'] += receipt_total
                payment_methods[method_key]['count'] += 1
            
            # 15% tax group
            if sales_15 > 0 or tax_15 > 0:
                key = f"15%_{receipt_currency}"
                if key not in tax_breakdown:
                    tax_breakdown[key] = {
                        'rate': '15%',
                        'tax_code': 'C',
                        'currency': receipt_currency,
                        'sales': Decimal('0'),
                        'tax': Decimal('0'),
                        'count': 0,
                        'payment_methods': {},
                    }
                tax_breakdown[key]['sales'] += sales_15
                tax_breakdown[key]['tax'] += tax_15
                tax_breakdown[key]['count'] += 1
                
                # Track payment methods for this tax group
                for payment in payment_methods_list:
                    method_name = payment.get('PaymentMethodName', 'OTHER').upper()
                    amount = Decimal(str(payment.get('PaymentAmt', 0)))
                    # Allocate proportionally based on sales
                    if receipt_total > 0:
                        allocated = sales_15 / receipt_total * amount
                    else:
                        allocated = Decimal('0')
                    
                    pm_key = method_name
                    if pm_key not in tax_breakdown[key]['payment_methods']:
                        tax_breakdown[key]['payment_methods'][pm_key] = Decimal('0')
                    tax_breakdown[key]['payment_methods'][pm_key] += allocated
            
            # 0% tax group
            if sales_0 > 0:
                key = f"0%_{receipt_currency}"
                if key not in tax_breakdown:
                    tax_breakdown[key] = {
                        'rate': '0%',
                        'tax_code': 'B',
                        'currency': receipt_currency,
                        'sales': Decimal('0'),
                        'tax': Decimal('0'),
                        'count': 0,
                        'payment_methods': {},
                    }
                tax_breakdown[key]['sales'] += sales_0
                tax_breakdown[key]['count'] += 1
                
                for payment in payment_methods_list:
                    method_name = payment.get('PaymentMethodName', 'OTHER').upper()
                    amount = Decimal(str(payment.get('PaymentAmt', 0)))
                    if receipt_total > 0:
                        allocated = sales_0 / receipt_total * amount
                    else:
                        allocated = Decimal('0')
                    
                    pm_key = method_name
                    if pm_key not in tax_breakdown[key]['payment_methods']:
                        tax_breakdown[key]['payment_methods'][pm_key] = Decimal('0')
                    tax_breakdown[key]['payment_methods'][pm_key] += allocated
            
            # Exempt tax group
            if sales_exempt > 0:
                key = f"Exempt_{receipt_currency}"
                if key not in tax_breakdown:
                    tax_breakdown[key] = {
                        'rate': 'Exempt',
                        'tax_code': 'A',
                        'currency': receipt_currency,
                        'sales': Decimal('0'),
                        'tax': Decimal('0'),
                        'count': 0,
                        'payment_methods': {},
                    }
                tax_breakdown[key]['sales'] += sales_exempt
                tax_breakdown[key]['count'] += 1
                
                for payment in payment_methods_list:
                    method_name = payment.get('PaymentMethodName', 'OTHER').upper()
                    amount = Decimal(str(payment.get('PaymentAmt', 0)))
                    if receipt_total > 0:
                        allocated = sales_exempt / receipt_total * amount
                    else:
                        allocated = Decimal('0')
                    
                    pm_key = method_name
                    if pm_key not in tax_breakdown[key]['payment_methods']:
                        tax_breakdown[key]['payment_methods'][pm_key] = Decimal('0')
                    tax_breakdown[key]['payment_methods'][pm_key] += allocated
        
        # Convert Decimal to float for JSON
        breakdown_list = []
        for key, data in tax_breakdown.items():
            # Build payment methods breakdown
            pm_breakdown = []
            for pm_key, pm_amount in data['payment_methods'].items():
                if pm_amount > 0:
                    pm_breakdown.append({
                        'method': pm_key,
                        'amount': float(pm_amount),
                    })
            
            breakdown_list.append({
                'rate': data['rate'],
                'tax_code': data['tax_code'],
                'currency': data['currency'],
                'sales': float(data['sales']),
                'tax': float(data['tax']),
                'count': data['count'],
                'payment_methods': pm_breakdown,
                'key': key,
            })
        
        # Sort by rate (15% first, then 0%, then Exempt)
        rate_order = {'15%': 0, '0%': 1, 'Exempt': 2}
        breakdown_list.sort(key=lambda x: (rate_order.get(x['rate'], 99), x['currency']))
        
        # Build payment methods summary
        payment_summary = []
        for key, data in payment_methods.items():
            if data['total'] > 0:
                payment_summary.append({
                    'currency': data['currency'],
                    'method': data['method'],
                    'total': float(data['total']),
                    'count': data['count'],
                })
        payment_summary.sort(key=lambda x: (x['currency'], x['method']))
        
        return JsonResponse({
            'success': True,
            'data': {
                'summary': {
                    'total_sales': float(total_sales),
                    'total_tax': float(total_tax),
                    'total_receipts': total_receipts,
                    'average_per_receipt': float(total_sales / total_receipts) if total_receipts > 0 else 0,
                    'currency': currency_used,
                },
                'breakdown': breakdown_list,
                'payment_summary': payment_summary,
                'filters': {
                    'date_from': date_from,
                    'date_to': date_to,
                    'currency': currency,
                    'status': status,
                }
            }
        })
        
    except Exception as e:
        logger.exception("Tax report error")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)



@login_required
def api_tax_report_summary(request):
    """
    Get quick tax report summary for dashboard.
    """
    try:
        # Get current month date range
        today = timezone.now().date()
        first_day = today.replace(day=1)
        
        receipts = FiscalReceipt.objects.filter(
            status=FiscalReceipt.STATUS_SYNCED,
            my_yyy_mm_dd_date__gte=first_day,
            my_yyy_mm_dd_date__lte=today
        )
        
        total_sales = Decimal('0')
        total_tax = Decimal('0')
        
        for receipt in receipts:
            sales_15 = Decimal(str(receipt.tax_15_perc_sales_total or 0))
            sales_0 = Decimal(str(receipt.zero_perc_sales_amt_total or 0))
            sales_exempt = Decimal(str(receipt.nontaxible_sales_amt_total or 0))
            tax_15 = Decimal(str(receipt.tax_amt_15_perc or 0))
            
            total_sales += sales_15 + sales_0 + sales_exempt
            total_tax += tax_15
        
        return JsonResponse({
            'success': True,
            'data': {
                'period': {
                    'from': first_day.isoformat(),
                    'to': today.isoformat(),
                },
                'total_sales': float(total_sales),
                'total_tax': float(total_tax),
                'total_receipts': receipts.count(),
            }
        })
        
    except Exception as e:
        logger.exception("Tax report summary error")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_tax_report_export(request):
    """
    Export tax report as CSV with tax code, currency, and payment method breakdown.
    """
    try:
        import csv
        from django.http import HttpResponse
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        currency = request.GET.get('currency')
        status = request.GET.get('status', 'SYNCED')
        
        # Build query
        receipts = FiscalReceipt.objects.filter(status=status)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                receipts = receipts.filter(my_yyy_mm_dd_date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                receipts = receipts.filter(my_yyy_mm_dd_date__lte=date_to_obj)
            except ValueError:
                pass
        
        if currency:
            receipts = receipts.filter(doc_currency=currency.upper())
        
        # Create CSV response
        try:
            from system_settings.models import SystemSetting
            comp_name = SystemSetting.get().company_name or 'Clarity Retail'
        except Exception:
            comp_name = 'Clarity Retail'
        clean_comp = comp_name.replace('_', ' ').strip()
        date_str = timezone.now().strftime('%Y-%m-%d')
        filename = f"{clean_comp} - Tax Report - {date_str}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Fiscal #', 'Local #', 'Type', 'Currency', 'Date',
            'Total', '15% Sales', '15% Tax', '0% Sales', 'Exempt Sales',
            'Payment Method', 'Payment Amount', 'Status', 'QR Code', 'Buyer'
        ])
        
        # Write data
        for receipt in receipts:
            # Get payment methods
            payment_methods = receipt.payment_lines if receipt.payment_lines else []
            
            if payment_methods:
                for payment in payment_methods:
                    writer.writerow([
                        receipt.inv_number or '',
                        receipt.local_receipt_number or '',
                        receipt.doc_type,
                        receipt.doc_currency,
                        receipt.my_yyy_mm_dd_date,
                        float(receipt.document_total) if receipt.document_total else 0,
                        float(receipt.tax_15_perc_sales_total or 0),
                        float(receipt.tax_amt_15_perc or 0),
                        float(receipt.zero_perc_sales_amt_total or 0),
                        float(receipt.nontaxible_sales_amt_total or 0),
                        payment.get('PaymentMethodName', 'OTHER'),
                        float(payment.get('PaymentAmt', 0)),
                        receipt.status,
                        receipt.qr_code_url or '',
                        receipt.buyer_register_name or '',
                    ])
            else:
                writer.writerow([
                    receipt.inv_number or '',
                    receipt.local_receipt_number or '',
                    receipt.doc_type,
                    receipt.doc_currency,
                    receipt.my_yyy_mm_dd_date,
                    float(receipt.document_total) if receipt.document_total else 0,
                    float(receipt.tax_15_perc_sales_total or 0),
                    float(receipt.tax_amt_15_perc or 0),
                    float(receipt.zero_perc_sales_amt_total or 0),
                    float(receipt.nontaxible_sales_amt_total or 0),
                    'CASH',
                    float(receipt.document_total) if receipt.document_total else 0,
                    receipt.status,
                    receipt.qr_code_url or '',
                    receipt.buyer_register_name or '',
                ])
        
        return response
        
    except Exception as e:
        logger.exception("Tax report export error")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
def api_update_receipt(request, receipt_id):
    """Update an unsynced receipt"""
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'error': 'PUT required'}, status=405)
    
    try:
        receipt = FiscalReceipt.objects.get(id=receipt_id)
        
        # Only allow editing PENDING receipts
        if receipt.status != FiscalReceipt.STATUS_PENDING:
            return JsonResponse({
                'success': False, 
                'error': f'Cannot edit receipt with status: {receipt.status}'
            })
        
        data = json.loads(request.body) if request.body else {}
        
        # Update buyer fields
        if 'buyer_register_name' in data:
            receipt.buyer_register_name = data['buyer_register_name']
        if 'buyer_TIN' in data:
            receipt.buyer_TIN = data['buyer_TIN']
        if 'VAT_number' in data:
            receipt.VAT_number = data['VAT_number']
        if 'phone_no' in data:
            receipt.phone_no = data['phone_no']
        if 'email' in data:
            receipt.email = data['email']
        
        # Update line items if provided
        if 'line_items' in data and data['line_items']:
            # Validate and update line items
            new_line_items = []
            for item in data['line_items']:
                if item.get('LineDescription'):
                    from reusable_functions.univesal.fiscalisation import is_correct_hs_code_format
                    hs_candidate = str(item.get('receiptLineHSCode') or '').strip()
                    if not is_correct_hs_code_format(hs_candidate):
                        hs_candidate = getattr(FiscalisationSettings.get_settings(), 'default_hs_code', '95069100')
                        if not is_correct_hs_code_format(hs_candidate):
                            hs_candidate = '95069100'
                    new_line_items.append({
                        'LineDescription': item.get('LineDescription', ''),
                        'UnitPrice': item.get('UnitPrice', '0'),
                        'Quantity': item.get('Quantity', '0'),
                        'Total': item.get('Total', '0'),
                        'IntTaxCode': item.get('IntTaxCode', 2),
                        'StrTaxCode': item.get('StrTaxCode', 'B'),
                        'TaxPercentage': item.get('TaxPercentage', '0'),
                        'receiptLineHSCode': hs_candidate,
                    })
            
            if new_line_items:
                receipt.line_items = new_line_items
                
                # Recalculate totals from line items
                new_total = sum(float(item.get('Total', 0)) for item in new_line_items)
                receipt.document_total = Decimal(str(new_total))
        
        receipt.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Receipt updated successfully',
            'receipt_id': receipt.id
        })
        
    except FiscalReceipt.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def api_stats(request):
    """Get dashboard statistics"""
    stats = get_fiscal_dashboard_stats()
    
    # Get last sync info
    last_sync = SyncLog.objects.filter(success=True).first()
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'fiscalisation_active': FiscalisationSettings.get_settings().is_fiscalisation_active(),
        'last_sync_at': last_sync.attempt_time.isoformat() if last_sync else None,
        'success_rate': SyncLog.objects.filter(success=True).count() / max(SyncLog.objects.count(), 1) * 100
    })


@login_required
def api_receipts(request):
    """Get receipts with pagination and filtering"""
    receipts = FiscalReceipt.objects.all().order_by('-created_at')
    
    # Filtering
    status = request.GET.get('status')
    doc_type = request.GET.get('type')
    currency = request.GET.get('currency')
    search = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        receipts = receipts.filter(status=status)
    if doc_type:
        receipts = receipts.filter(doc_type=doc_type)
    if currency:
        receipts = receipts.filter(doc_currency=currency)
    if search:
        receipts = receipts.filter(
            Q(inv_number__icontains=search) |
            Q(local_receipt_number__icontains=search) |
            Q(buyer_register_name__icontains=search) |
            Q(buyer_TIN__icontains=search)
        )
    if date_from:
        receipts = receipts.filter(created_at__date__gte=date_from)
    if date_to:
        receipts = receipts.filter(created_at__date__lte=date_to)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    total = receipts.count()
    start = (page - 1) * per_page
    end = start + per_page
    receipts_page = receipts[start:end]
    
    # Get available filters
    available_statuses = FiscalReceipt.objects.values_list('status', flat=True).distinct()
    available_types = FiscalReceipt.objects.values_list('doc_type', flat=True).distinct()
    available_currencies = FiscalReceipt.objects.values_list('doc_currency', flat=True).distinct()
    
    # Build response data
    data = []
    status_choices = dict(FiscalReceipt.STATUS_CHOICES)
    type_choices = dict(FiscalReceipt.TYPE_CHOICES)
    
    for receipt in receipts_page:
        data.append({
            'id': receipt.id,
            'inv_number': receipt.inv_number,
            'local_receipt_number': receipt.local_receipt_number,
            'doc_type': receipt.doc_type,
            'doc_type_display': type_choices.get(receipt.doc_type, receipt.doc_type),
            'doc_currency': receipt.doc_currency,
            'document_total': float(receipt.document_total),
            'status': receipt.status,
            'status_display': status_choices.get(receipt.status, receipt.status),
            'buyer_register_name': receipt.buyer_register_name,
            'qr_code_url': receipt.qr_code_url,
            'created_at': receipt.created_at.isoformat(),
            'synced_at': receipt.synced_at.isoformat() if receipt.synced_at else None,
            'last_error': receipt.last_error,
            'retry_count': receipt.retry_count,
            'can_retry': receipt.can_retry(),
        })
    
    return JsonResponse({
        'success': True,
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'filters': {
            'available_statuses': list(available_statuses),
            'available_types': list(available_types),
            'available_currencies': list(available_currencies),
        }
    })


@login_required
def api_receipt_detail(request, receipt_id):
    """Get single receipt details"""
    try:
        receipt = FiscalReceipt.objects.get(id=receipt_id)
    except FiscalReceipt.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)
    
    # Get sync logs for this receipt
    logs = SyncLog.objects.filter(fiscal_receipt=receipt).order_by('-attempt_time')
    
    status_choices = dict(FiscalReceipt.STATUS_CHOICES)
    type_choices = dict(FiscalReceipt.TYPE_CHOICES)
    
    data = {
        'id': receipt.id,
        'inv_number': receipt.inv_number,
        'local_receipt_number': receipt.local_receipt_number,
        'doc_type': receipt.doc_type,
        'doc_type_display': type_choices.get(receipt.doc_type, receipt.doc_type),
        'doc_currency': receipt.doc_currency,
        'document_total': float(receipt.document_total),
        'status': receipt.status,
        'status_display': status_choices.get(receipt.status, receipt.status),
        'qr_code_url': receipt.qr_code_url,
        'buyer_register_name': receipt.buyer_register_name,
        'buyer_TIN': receipt.buyer_TIN,
        'VAT_number': receipt.VAT_number,
        'phone_no': receipt.phone_no,
        'email': receipt.email,
        'invoice_number_to_credit_debit': receipt.invoice_number_to_credit_debit,
        'created_at': receipt.created_at.isoformat(),
        'synced_at': receipt.synced_at.isoformat() if receipt.synced_at else None,
        'last_error': receipt.last_error,
        'retry_count': receipt.retry_count,
        'my_yyy_mm_dd_date': receipt.my_yyy_mm_dd_date.isoformat(),
        'my_24hr_time_format_with_seconds': receipt.my_24hr_time_format_with_seconds,
        'nontaxible_sales_amt_total': float(receipt.nontaxible_sales_amt_total),
        'zero_per_taxamt': float(receipt.zero_per_taxamt),
        'zero_perc_sales_amt_total': float(receipt.zero_perc_sales_amt_total),
        'tax_amt_15_perc': float(receipt.tax_amt_15_perc),
        'tax_15_perc_sales_total': float(receipt.tax_15_perc_sales_total),
        'line_items': receipt.line_items,
        'payment_lines': receipt.payment_lines,
        'binary_server_response': receipt.binary_server_response,
        'logs': [{
            'attempt_time': log.attempt_time.isoformat(),
            'success': log.success,
            'duration_ms': log.duration_ms,
            'error_message': log.error_message,
            'synced_count': log.synced_count,
            'failed_count': log.failed_count,
        } for log in logs[:20]]
    }
    
    return JsonResponse({'success': True, 'data': data})


@login_required
@csrf_exempt
def api_sync_receipt(request, receipt_id):
    """Sync a single receipt"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        receipt = FiscalReceipt.objects.get(id=receipt_id)
        
        if receipt.status == FiscalReceipt.STATUS_SYNCED:
            return JsonResponse({'success': False, 'error': 'Receipt already synced'})
        
        if receipt.status == FiscalReceipt.STATUS_PROCESSING:
            return JsonResponse({'success': False, 'error': 'Receipt is being processed'})
        
        # Start sync in background
        sync_receipt_async(receipt_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Sync started in background',
            'receipt_id': receipt_id
        })
        
    except FiscalReceipt.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)


@login_required
@csrf_exempt
def api_sync_all(request):
    """Sync all pending receipts"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    data = json.loads(request.body) if request.body else {}
    limit = data.get('limit', 100)
    
    result = sync_pending_receipts(limit=limit, async_mode=True)
    
    return JsonResponse({
        'success': True,
        'result': result
    })


@login_required
@csrf_exempt
def api_retry_failed(request):
    """Retry failed receipts"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    data = json.loads(request.body) if request.body else {}
    limit = data.get('limit', 50)
    
    result = retry_failed_receipts(limit=limit, async_mode=True)
    
    return JsonResponse({
        'success': True,
        'result': result
    })


@login_required
@csrf_exempt
def api_toggle_fiscalisation(request):
    """Toggle fiscalisation on/off"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        settings_obj = FiscalisationSettings.get_settings()
        data = json.loads(request.body) if request.body else {}
        
        action = data.get('action', 'toggle')
        
        if action == 'pause':
            settings_obj.pause(
                reason=data.get('reason', 'Admin action'),
                user=request.user.username
            )
            return JsonResponse({
                'success': True,
                'active': False,
                'message': 'Fiscalisation paused successfully'
            })
        
        elif action == 'resume':
            settings_obj.resume()
            return JsonResponse({
                'success': True,
                'active': True,
                'message': 'Fiscalisation resumed successfully'
            })
        
        else:  # toggle
            if settings_obj.is_fiscalisation_active():
                settings_obj.pause(
                    reason='Toggled off by admin',
                    user=request.user.username
                )
                return JsonResponse({
                    'success': True,
                    'active': False,
                    'message': 'Fiscalisation paused successfully'
                })
            else:
                settings_obj.resume()
                return JsonResponse({
                    'success': True,
                    'active': True,
                    'message': 'Fiscalisation resumed successfully'
                })
                
    except Exception as e:
        logger.exception("Toggle fiscalisation error")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        

@login_required
@csrf_exempt
def api_bulk_action(request):
    """Bulk actions on receipts"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    data = json.loads(request.body) if request.body else {}
    receipt_ids = data.get('receipt_ids', [])
    action = data.get('action', '')
    
    if not receipt_ids:
        return JsonResponse({'success': False, 'error': 'No receipts selected'})
    
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    
    for receipt_id in receipt_ids:
        try:
            receipt = FiscalReceipt.objects.get(id=receipt_id)
            
            if action == 'retry':
                if receipt.status in [FiscalReceipt.STATUS_FAILED, FiscalReceipt.STATUS_PENDING]:
                    receipt.mark_pending()
                    sync_receipt_async(receipt_id)
                    results['success'] += 1
                else:
                    results['skipped'] += 1
            
            elif action == 'reset':
                receipt.retry_count = 0
                receipt.mark_pending()
                results['success'] += 1
            
            elif action == 'void':
                if receipt.status != FiscalReceipt.STATUS_SYNCED:
                    receipt.status = FiscalReceipt.STATUS_VOID
                    receipt.save()
                    results['success'] += 1
                else:
                    results['skipped'] += 1
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown action: {action}'
                })
                
        except FiscalReceipt.DoesNotExist:
            results['failed'] += 1
    
    return JsonResponse({
        'success': True,
        'results': results,
        'action': action
    })


@login_required
@csrf_exempt
def api_test_connection(request):
    """Test connection to Binary API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    settings_obj = FiscalisationSettings.get_settings()
    
    if not settings_obj.device_id:
        return JsonResponse({'success': False, 'error': 'Device ID not configured'})
    
    try:
        result = get_device_status()
        
        if result and isinstance(result, dict) and 'error' not in result:
            return JsonResponse({
                'success': True,
                'message': 'Connection successful!',
                'response': result
            })
        elif isinstance(result, str) and 'error' not in result.lower():
            return JsonResponse({
                'success': True,
                'message': 'Connection successful!',
                'response': result
            })
        else:
            error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
            return JsonResponse({'success': False, 'error': error_msg})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_tax_config(request):
    """Get tax configuration from Binary API"""
    try:
        result = get_config_tax()
        return JsonResponse({'success': True, 'data': result})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def api_void_receipt(request, receipt_id):
    """Void a receipt"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        receipt = FiscalReceipt.objects.get(id=receipt_id)
        
        if receipt.status == FiscalReceipt.STATUS_SYNCED:
            return JsonResponse({
                'success': False,
                'error': 'Cannot void synced receipt - create a credit note instead'
            })
        
        receipt.status = FiscalReceipt.STATUS_VOID
        receipt.save()
        
        return JsonResponse({'success': True, 'message': 'Receipt voided successfully'})
        
    except FiscalReceipt.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)


@login_required
@csrf_exempt
def api_settings(request):
    """Get or update settings"""
    settings_obj = FiscalisationSettings.get_settings()
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'data': {
                'api_base_url': settings_obj.api_base_url,
                'device_id': settings_obj.device_id,
                'machine_code': settings_obj.machine_code,
                'api_password': settings_obj.api_password,
                'qr_url': settings_obj.qr_url,
                'sync_interval_seconds': settings_obj.sync_interval_seconds,
                'max_retry_count': settings_obj.max_retry_count,
                'admin_email': settings_obj.admin_email,
                'admin_phone': settings_obj.admin_phone,
                'default_hs_code': settings_obj.default_hs_code,
                'auto_resume_on_success': settings_obj.auto_resume_on_success,
                'fiscalisation_enabled': settings_obj.fiscalisation_enabled,
            }
        })
    
    elif request.method == 'POST':
        data = json.loads(request.body) if request.body else {}
        
        settings_obj.api_base_url = data.get('api_base_url', settings_obj.api_base_url)
        settings_obj.device_id = data.get('device_id', settings_obj.device_id)
        settings_obj.machine_code = data.get('machine_code', settings_obj.machine_code)
        settings_obj.api_password = data.get('api_password', settings_obj.api_password)
        settings_obj.qr_url = data.get('qr_url', settings_obj.qr_url)
        if 'default_hs_code' in data:
            new_hs = str(data.get('default_hs_code', '')).strip()
            if new_hs:
                from reusable_functions.univesal.fiscalisation import is_correct_hs_code_format
                if not is_correct_hs_code_format(new_hs):
                    return JsonResponse({'success': False, 'error': 'Default ZIMRA HS Code must be exactly 8 digits without dots or spaces (e.g. 95069100).'}, status=400)
                settings_obj.default_hs_code = new_hs
        settings_obj.sync_interval_seconds = int(data.get('sync_interval_seconds', 30))
        settings_obj.max_retry_count = int(data.get('max_retry_count', 5))
        settings_obj.admin_email = data.get('admin_email', '')
        settings_obj.admin_phone = data.get('admin_phone', '')
        settings_obj.auto_resume_on_success = data.get('auto_resume_on_success', True)
        settings_obj.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Settings saved successfully'
        })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def api_logs(request):
    """Get sync logs with pagination"""
    logs = SyncLog.objects.all().order_by('-attempt_time')
    
    # Filtering
    success = request.GET.get('success')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if success in ['true', 'false']:
        logs = logs.filter(success=success == 'true')
    if date_from:
        logs = logs.filter(attempt_time__date__gte=date_from)
    if date_to:
        logs = logs.filter(attempt_time__date__lte=date_to)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    total = logs.count()
    start = (page - 1) * per_page
    end = start + per_page
    logs_page = logs[start:end]
    
    data = [{
        'id': log.id,
        'receipt_id': log.fiscal_receipt_id,
        'receipt_number': log.fiscal_receipt.inv_number if log.fiscal_receipt else None,
        'attempt_time': log.attempt_time.isoformat(),
        'success': log.success,
        'synced_count': log.synced_count,
        'failed_count': log.failed_count,
        'duration_ms': log.duration_ms,
        'error_message': log.error_message,
        'response_code': log.response_code,
    } for log in logs_page]
    
    return JsonResponse({
        'success': True,
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    })