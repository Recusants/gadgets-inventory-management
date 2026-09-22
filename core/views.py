"""Function-based views for core utilities, settings, and system tests."""
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from .models import CompanySetting
from .validators import validate_company_settings
from .responses import success_response, error_response
from .decorators import ajax_required

def test_modal(request):
    """Return partial HTML for the test modal."""
    return render(request, 'core/test_modal.html')

def test_ajax(request):
    """Return canonical success envelope for AJAX verification."""
    return success_response(
        title="AJAX Connected",
        message="jQuery $.ajax connected with uniform JSON response envelope.",
        data={"status": "online"}
    )

from django.shortcuts import render, redirect
from django.contrib import messages

import sys
import os
import platform
import django
from django.conf import settings

def settings_view(request):
    """Render company contact and printed receipt settings for the store using this software."""
    settings_obj = CompanySetting.get_settings()
    return render(request, 'core/settings.html', {'settings': settings_obj})

def system_view(request):
    """Render comprehensive software details and developer support provider information (avail.co.zw)."""
    from accounts.models import User
    from inventory.models import Product
    from sales.models import Sale
    from .version import get_system_version
    
    db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]
    db_name = str(settings.DATABASES['default'].get('NAME', 'Default'))
    if 'sqlite' in db_engine.lower() and ('/' in db_name or '\\' in db_name):
        db_name = os.path.basename(db_name)

    client_settings = CompanySetting.get_settings()
    sys_ver = get_system_version()

    context = {
        'software_info': {
            'name': 'Clarity Retail: Gadgets store',
            'short_name': 'Clarity Retail',
            'edition': 'Enterprise Retail Edition',
            'version': sys_ver.get('version', 'v2.4.2'),
            'build': sys_ver.get('build', 'v2.4.2-git'),
            'commit_hash': sys_ver.get('commit_hash', 'latest'),
            'branch': sys_ver.get('branch', 'main'),
            'last_updated': sys_ver.get('updated_at', timezone.now().strftime('%Y-%m-%d %H:%M')),
            'status': 'Operational & Active',
            'license_type': 'Commercial Single-Tenant License',
            'client_store_name': client_settings.company_name or 'Gadget Retail Store',
            'currency': f"{client_settings.currency_symbol} ({client_settings.currency_code})",
        },
        'developer_info': {
            'company_name': 'Avail Software (Avail Technologies Pvt Ltd)',
            'short_brand': 'Avail Software',
            'tagline': 'Scalable, Secure & Innovative Software Solutions in Zimbabwe & Beyond',
            'website': 'https://avail.co.zw',
            'domain': 'avail.co.zw',
            'email': 'info@avail.co.zw',
            'support_email': 'info@avail.co.zw',
            'primary_phone': '+263 78 485 1863',
            'secondary_phone': '+263 78 610 6154',
            'address': '1788 Ruvimbo Park, Marondera, Zimbabwe',
            'regional_hub': 'Harare, Zimbabwe',
            'services': [
                'Custom Business Software & Web App Development',
                'Retail Inventory, POS & Multi-Branch Systems',
                'Pharmacy & Clinic Management Solutions',
                'Enterprise ERP & Financial Ledger Architecture',
                'Cybersecurity, Cloud Infrastructure & Digital Transformation',
                'Continuous Support, SLAs & Disaster Recovery'
            ],
            'copyright': '© 2026 Avail Technologies (Pvt) Ltd. All rights reserved.'
        },
        'environment_info': {
            'django_version': django.get_version(),
            'python_version': sys.version.split()[0],
            'os_platform': f"{platform.system()} {platform.release()}",
            'db_engine': db_engine.upper(),
            'db_name': db_name,
            'debug_mode': settings.DEBUG,
            'server_time': timezone.now(),
            'total_users': User.objects.count() if hasattr(User, 'objects') else 0,
            'total_products': Product.objects.count() if hasattr(Product, 'objects') else 0,
            'total_sales': Sale.objects.count() if hasattr(Sale, 'objects') else 0,
        }
    }
    return render(request, 'core/system.html', context)



@require_POST
def settings_save(request):
    """Save company settings via jQuery AJAX with fallback redirect."""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    errors = validate_company_settings(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Validation Error",
                message="Please correct the highlighted errors.",
                errors=errors
            )
        messages.error(request, "Please correct the errors in the form.")
        return redirect('core:settings')

    settings_obj = CompanySetting.get_settings()
    settings_obj.company_name = request.POST.get('company_name', '').strip()
    settings_obj.tagline = request.POST.get('tagline', '').strip()
    settings_obj.phone = request.POST.get('phone', '').strip()
    settings_obj.email = request.POST.get('email', '').strip()
    settings_obj.address = request.POST.get('address', '').strip()
    settings_obj.currency_symbol = request.POST.get('currency_symbol', '').strip()
    settings_obj.currency_code = request.POST.get('currency_code', '').strip()
    settings_obj.receipt_header_note = request.POST.get('receipt_header_note', '').strip()
    settings_obj.receipt_footer_note = request.POST.get('receipt_footer_note', '').strip()
    if 'logo' in request.FILES:
        settings_obj.logo = request.FILES['logo']
    settings_obj.is_customized = True
    settings_obj.save()


    if is_ajax:
        return success_response(
            title="Settings Updated",
            message="Company contact details and receipt customization saved successfully."
        )
    messages.success(request, "Company contact details and receipt customization saved successfully.")
    return redirect('core:settings')


@require_POST
def setup_initialize(request):
    """
    Handle initial store setup form submission:
    - Updates CompanySetting (company_name, phone, currency, address, email, logo)
    - Creates initial Category if given
    - Creates initial Supplier if given
    - Ensures default Customer ("Walk-in Customer")
    - Creates initial ExpenseCategory if given
    - Sets is_customized = True
    """
    from django.db import transaction
    from inventory.models import Category, Supplier
    from sales.models import Customer
    from expenses.models import ExpenseCategory

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    company_name = request.POST.get('company_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    category_name = request.POST.get('category_name', '').strip()
    supplier_name = request.POST.get('supplier_name', '').strip()

    errors = {}
    if not company_name:
        errors['company_name'] = "Operating Store / Company name is required."
    if not phone:
        errors['phone'] = "Official contact phone number is required."

    if errors:
        if is_ajax:
            return error_response(
                title="Store Setup Incomplete",
                message="Please provide your store name and contact phone number to continue.",
                errors=errors
            )
        return redirect('dashboard:index')


    with transaction.atomic():
        # 1. Update CompanySetting
        settings_obj = CompanySetting.get_settings()
        settings_obj.company_name = company_name
        settings_obj.phone = phone
        if request.POST.get('tagline'):
            settings_obj.tagline = request.POST.get('tagline', '').strip()
        if request.POST.get('email'):
            settings_obj.email = request.POST.get('email', '').strip()
        if request.POST.get('address'):
            settings_obj.address = request.POST.get('address', '').strip()
        if request.POST.get('currency_symbol'):
            settings_obj.currency_symbol = request.POST.get('currency_symbol', '').strip()
        if request.POST.get('currency_code'):
            settings_obj.currency_code = request.POST.get('currency_code', '').strip().upper()
        if 'logo' in request.FILES:
            settings_obj.logo = request.FILES['logo']
        settings_obj.is_customized = True
        settings_obj.save()

        # 2. Create Initial Category
        if category_name:
            Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"Initial product category for {company_name}"}
            )

        # 3. Create Initial Supplier
        if supplier_name:
            Supplier.objects.get_or_create(
                name=supplier_name,
                defaults={
                    "phone": request.POST.get('supplier_phone', '').strip(),
                    "notes": "Initial registered supplier created during setup wizard."
                }
            )

        # 4. Ensure Default Customer
        Customer.get_default_customer()

        # 5. Create Initial ExpenseCategory
        exp_name = request.POST.get('expense_category_name', '').strip() or 'General & Operational Expenses'
        ExpenseCategory.objects.get_or_create(
            name=exp_name,
            defaults={"description": "Standard business operations and overheads"}
        )

    if is_ajax:
        return success_response(
            title="Store Initialized",
            message=f'Welcome to {settings_obj.company_name}! Mandatory foundational data has been configured.',
            data={"reload": True}
        )
    return redirect('dashboard:index')


# ==============================================================================
# NOTIFICATIONS
# ==============================================================================


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Notification
from .utils import sync_low_stock_notifications

def notification_list_view(request):
    """Render full shell for Notifications page."""
    sync_low_stock_notifications()
    queryset = Notification.objects.select_related('product', 'product__stock').all().order_by('-created_at')
    
    total_count = queryset.count()
    unread_count = queryset.filter(is_read=False).count()
    low_stock_alerts_count = queryset.filter(notification_type=Notification.NotificationType.LOW_STOCK, is_read=False).count()

    paginator = Paginator(queryset, 10)
    notifications = paginator.page(1)
    return render(request, 'core/notification_list.html', {
        'notifications': notifications,
        'paginator': paginator,
        'total_count': total_count,
        'unread_count': unread_count,
        'low_stock_alerts_count': low_stock_alerts_count,
    })


def notification_table_partial(request):
    """Filterable partial for Notifications."""
    sync_low_stock_notifications()
    filter_type = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Notification.objects.select_related('product', 'product__stock').all().order_by('-created_at')

    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(message__icontains=query))
    if filter_type:
        queryset = queryset.filter(notification_type=filter_type)
    if status_filter == 'unread':
        queryset = queryset.filter(is_read=False)
    elif status_filter == 'read':
        queryset = queryset.filter(is_read=True)

    paginator = Paginator(queryset, 10)
    try:
        notifications = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        notifications = paginator.page(1)

    return render(request, 'core/partials/notification_table.html', {
        'notifications': notifications,
        'paginator': paginator,
        'total_count': paginator.count,
    })


@require_POST
def notification_mark_read(request, pk):
    """Mark a single notification as read."""
    notif = Notification.objects.filter(pk=pk).first()
    if notif:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return success_response(title="Marked as Read", message="Notification marked as read.")


@require_POST
def notification_mark_all_read(request):
    """Mark all unread notifications as read."""
    Notification.objects.filter(is_read=False).update(is_read=True)
    return success_response(title="All Read", message="All notifications marked as read.")


@require_POST
def notification_delete(request, pk):
    """Delete a notification."""
    notif = Notification.objects.filter(pk=pk).first()
    if notif:
        notif.delete()
    return success_response(title="Deleted", message="Notification removed.")


# ==============================================================================
# UNIVERSAL DATABASE BACKUP & RESTORE (SQLite, PostgreSQL, Docker)
# ==============================================================================

def db_backup_download(request):
    """
    Download database backup.
    Supports 'json' (Universal DB-agnostic fixture) and 'sqlite' (Raw SQLite binary).
    """
    import io
    import os
    from django.utils import timezone
    from django.core.management import call_command
    from django.conf import settings
    from django.http import HttpResponse

    fmt = request.GET.get('format', 'json').lower()
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

    if fmt == 'sqlite':
        db_engine = settings.DATABASES['default']['ENGINE'].lower()
        if 'sqlite' in db_engine:
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                with open(db_path, 'rb') as f:
                    content = f.read()
                response = HttpResponse(content, content_type='application/x-sqlite3')
                response['Content-Disposition'] = f'attachment; filename="gadget_store_raw_{timestamp}.sqlite3"'
                return response
            else:
                return error_response(title="File Not Found", message="SQLite database file not found on disk.")
        else:
            return error_response(
                title="Engine Incompatible",
                message="Active database is not SQLite. Please download the Universal JSON backup instead."
            )

    # Universal JSON fixture export (works on SQLite, PostgreSQL, and Docker)
    buf = io.StringIO()
    try:
        call_command(
            'dumpdata',
            'accounts.User',
            'core.CompanySetting',
            'core.Notification',
            'inventory',
            'sales',
            'expenses',
            format='json',
            indent=2,
            use_natural_foreign_keys=True,
            use_natural_primary_keys=True,
            stdout=buf
        )
        data = buf.getvalue()
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="gadget_store_backup_{timestamp}.json"'
        return response
    except Exception as e:
        return error_response(title="Backup Failed", message=f"Failed to generate backup: {str(e)}")


@require_POST
def db_backup_restore(request):
    """
    Restore database from an uploaded JSON or SQLite file.
    Supports Overwrite and Merge modes.
    Works universally across SQLite, PostgreSQL, and Docker containers.
    """
    import os
    import json
    import tempfile
    from django.db import connection, transaction
    from django.core.management import call_command
    from django.conf import settings

    upload_file = request.FILES.get('backup_file')
    restore_mode = request.POST.get('restore_mode', 'merge')  # 'overwrite' or 'merge'

    if not upload_file:
        return error_response(title="No File Selected", message="Please choose a backup file (.json or .sqlite3) to restore.")

    fname = upload_file.name.lower()

    import time
    start_time = time.time()

    if fname.endswith('.sqlite3') or fname.endswith('.db'):
        db_engine = settings.DATABASES['default']['ENGINE'].lower()
        if 'sqlite' not in db_engine:
            return error_response(
                title="Engine Incompatible",
                message="Raw .sqlite3 backup files can only be restored on SQLite databases. For PostgreSQL or Docker, use the Universal JSON format."
            )
        try:
            db_path = settings.DATABASES['default']['NAME']
            connection.close()
            with open(db_path, 'wb+') as dest:
                for chunk in upload_file.chunks():
                    dest.write(chunk)
            elapsed = round(time.time() - start_time, 2)
            return success_response(
                title="Database Restored Successfully",
                message=f"Raw SQLite database restored successfully ({round(upload_file.size / 1024, 1)} KB).",
                data={
                    'reload': True,
                    'format': 'SQLITE',
                    'filename': upload_file.name,
                    'size_kb': round(upload_file.size / 1024, 1),
                    'mode': 'OVERWRITE',
                    'elapsed_seconds': elapsed,
                    'restored_at': timezone.now().strftime('%d %b %Y, %H:%M:%S')
                }
            )
        except Exception as e:
            return error_response(title="Restore Failed", message=f"Failed to restore SQLite binary file: {str(e)}")

    elif fname.endswith('.json'):
        try:
            raw_data = upload_file.read().decode('utf-8')
            parsed_records = json.loads(raw_data)  # Validate valid JSON
        except Exception as e:
            return error_response(title="Invalid JSON", message=f"The uploaded file is not valid JSON: {str(e)}")

        total_records = len(parsed_records)
        model_counts = {}
        for r in parsed_records:
            m = r.get('model', 'entry')
            short_name = m.split('.')[-1].capitalize()
            model_counts[short_name] = model_counts.get(short_name, 0) + 1

        # Create temporary file for loaddata command
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json')
        try:
            with open(temp_fd, 'w', encoding='utf-8') as tf:
                tf.write(raw_data)

            with transaction.atomic():
                if restore_mode == 'overwrite':
                    from sales.models import SalePayment, SaleItem, Sale, Customer
                    from expenses.models import Expense, ExpenseCategory
                    from inventory.models import StockMovement, StockBatch, Stock, Product, Supplier, Category
                    from core.models import Notification

                    SalePayment.objects.all().delete()
                    SaleItem.objects.all().delete()
                    Sale.objects.all().delete()
                    Customer.objects.all().delete()
                    Expense.objects.all().delete()
                    ExpenseCategory.objects.all().delete()
                    StockMovement.objects.all().delete()
                    StockBatch.objects.all().delete()
                    Stock.objects.all().delete()
                    Product.objects.all().delete()
                    Supplier.objects.all().delete()
                    Category.objects.all().delete()
                    Notification.objects.all().delete()

                # Load serialized fixture
                call_command('loaddata', temp_path)

            elapsed = round(time.time() - start_time, 2)
            mode_label = "overwritten and restored" if restore_mode == 'overwrite' else "merged"
            return success_response(
                title="Database Restored Successfully",
                message=f"Database data was successfully {mode_label} from JSON backup ({total_records} records restored).",
                data={
                    'reload': True,
                    'format': 'JSON',
                    'filename': upload_file.name,
                    'size_kb': round(upload_file.size / 1024, 1),
                    'mode': restore_mode.upper(),
                    'total_records': total_records,
                    'model_counts': model_counts,
                    'elapsed_seconds': elapsed,
                    'restored_at': timezone.now().strftime('%d %b %Y, %H:%M:%S')
                }
            )
        except Exception as e:
            return error_response(
                title="Restore Failed",
                message=f"Restoration failed and was safely rolled back: {str(e)}"
            )
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    else:
        return error_response(
            title="Unsupported File",
            message="Please upload a .json backup file (Universal) or a .sqlite3 database file."
        )

