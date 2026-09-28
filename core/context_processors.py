from .models import CompanySetting, Notification
from .version import get_system_version
from inventory.models import Stock


def company_settings_processor(request):
    """
    Globally provides company settings and low-stock notification alerts to all templates.
    """
    settings_obj = CompanySetting.get_settings()
    
    # Auto-generate or sync low-stock and expiry notifications if needed
    try:
        from .utils import sync_all_stock_notifications
        sync_all_stock_notifications()
        unread_notifications = Notification.objects.select_related('product', 'product__stock', 'batch').filter(is_read=False).order_by('-created_at')[:6]
        unread_notifications_count = Notification.objects.filter(is_read=False).count()
        low_stock_count = Notification.objects.filter(is_read=False, notification_type=Notification.NotificationType.LOW_STOCK).count()
        expiry_count = Notification.objects.filter(is_read=False, notification_type=Notification.NotificationType.EXPIRING).count()
    except Exception:
        unread_notifications = []
        unread_notifications_count = 0
        low_stock_count = 0
        expiry_count = 0

    # Evaluate Mandatory Operational Data Checklist (Strictly Operating Store Settings)
    has_company_profile = False
    needs_mandatory_setup = False
    mandatory_checklist = []

    try:
        if request.user.is_authenticated:
            # Critical items are strictly the operating company settings
            has_store_name = bool(settings_obj.company_name and settings_obj.company_name.strip())
            has_phone = bool(settings_obj.phone and settings_obj.phone != "+263 77 123 4567")
            has_currency = bool(settings_obj.currency_symbol and settings_obj.currency_code)
            has_logo = bool(settings_obj.logo)
            has_company_profile = bool(settings_obj.is_customized and has_store_name and has_phone)

            mandatory_checklist = [
                {
                    'id': 'company_name',
                    'title': 'Store Name',
                    'description': 'Official operating store name required for printed receipts and invoices',
                    'is_configured': has_store_name,
                    'url': '/settings/'
                },
                {
                    'id': 'phone',
                    'title': 'Contact Phone',
                    'description': 'Store telephone / WhatsApp number printed on customer receipts',
                    'is_configured': has_phone,
                    'url': '/settings/'
                },
                {
                    'id': 'currency',
                    'title': 'Currency Setup',
                    'description': 'Default POS billing currency symbol and currency code (e.g. $, USD)',
                    'is_configured': has_currency,
                    'url': '/settings/'
                },
                {
                    'id': 'logo',
                    'title': 'Store Logo',
                    'description': 'Custom brand logo printed on invoices, topbar, and customer receipts',
                    'is_configured': has_logo,
                    'url': '/settings/'
                },
            ]
            needs_mandatory_setup = not has_company_profile
    except Exception:
        pass


    import platform
    import sys
    import django
    from django.conf import settings
    db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1].upper()

    sys_ver = get_system_version()
    system_details = {
        'system_name': sys_ver.get('system_name', 'Clarity Retail: Gadgets store'),
        'short_name': sys_ver.get('short_name', 'Clarity Retail'),
        'edition': 'Enterprise Retail Edition',
        'version': sys_ver.get('version', 'v2.4.8'),
        'build': sys_ver.get('build', 'v2.4.8-236657a'),
        'commit_hash': sys_ver.get('commit_hash', '236657a'),
        'branch': sys_ver.get('branch', 'main'),
        'db_engine': db_engine,
        'os_platform': f"{platform.system()} {platform.release()}",
        'python_version': f"Python {sys.version.split()[0]}",
        'django_version': f"Django {django.get_version()}",
        'developer_name': 'Avail Technologies (Pvt) Ltd',
        'developer_website': 'avail.co.zw',
    }

    return {
        'system_name': sys_ver.get('system_name', 'Clarity Retail: Gadgets store'),
        'system_short_name': sys_ver.get('short_name', 'Clarity Retail'),
        'system_version': sys_ver,
        'system_details': system_details,
        'company_settings': settings_obj,
        'settings': settings_obj,  # backwards compatibility
        'unread_notifications': unread_notifications,
        'unread_notifications_count': unread_notifications_count,
        'low_stock_count': low_stock_count,
        'expiry_count': expiry_count,
        'needs_mandatory_setup': needs_mandatory_setup,
        'mandatory_checklist': mandatory_checklist,
        'has_company_profile': has_company_profile,
    }


