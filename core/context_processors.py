from .models import CompanySetting, Notification
from .version import get_system_version
from inventory.models import Stock


def company_settings_processor(request):
    """
    Globally provides company settings and low-stock notification alerts to all templates.
    """
    settings_obj = CompanySetting.get_settings()
    
    # Auto-generate or sync low-stock notifications if needed
    try:
        from .utils import sync_low_stock_notifications
        sync_low_stock_notifications()
        unread_notifications = Notification.objects.select_related('product', 'product__stock').filter(is_read=False).order_by('-created_at')[:6]
        unread_notifications_count = Notification.objects.filter(is_read=False).count()
        low_stock_count = Notification.objects.filter(is_read=False, notification_type=Notification.NotificationType.LOW_STOCK).count()
    except Exception:
        unread_notifications = []
        unread_notifications_count = 0
        low_stock_count = 0

    # Evaluate Mandatory Operational Data Checklist
    has_categories = False
    has_suppliers = False
    has_customers = False
    has_expense_categories = False
    has_company_profile = False
    needs_mandatory_setup = False
    mandatory_checklist = []

    try:
        if request.user.is_authenticated:
            from inventory.models import Category, Supplier
            from sales.models import Customer
            from expenses.models import ExpenseCategory

            has_categories = Category.objects.exists()
            has_suppliers = Supplier.objects.exists()
            has_customers = Customer.objects.exists()
            has_expense_categories = ExpenseCategory.objects.exists()
            has_company_profile = bool(settings_obj.is_customized or (settings_obj.phone and settings_obj.phone != "+263 77 123 4567"))

            mandatory_checklist = [
                {
                    'id': 'company_profile',
                    'title': 'Company Profile & Logo',
                    'description': 'Store name, contact phone, currency, and custom receipt logo',
                    'is_configured': has_company_profile,
                    'url': '/settings/'
                },
                {
                    'id': 'category',
                    'title': 'Product Categories',
                    'description': 'Mandatory for cataloging merchandise and products (0 found)',
                    'is_configured': has_categories,
                    'url': '/inventory/categories/'
                },
                {
                    'id': 'supplier',
                    'title': 'Registered Suppliers',
                    'description': 'Mandatory to intake inventory and receive purchase invoices (0 found)',
                    'is_configured': has_suppliers,
                    'url': '/inventory/suppliers/'
                },
                {
                    'id': 'customer',
                    'title': 'Default Walk-in Customer',
                    'description': 'Foundational counter customer required for POS checkouts',
                    'is_configured': has_customers,
                    'url': '/sales/customers/'
                },
                {
                    'id': 'expense_category',
                    'title': 'Expense Categories',
                    'description': 'Categorization for operational expenses and store overhead',
                    'is_configured': has_expense_categories,
                    'url': '/expenses/categories/'
                },
            ]
            needs_mandatory_setup = not (has_categories and has_suppliers and has_company_profile)
    except Exception:
        pass

    sys_ver = get_system_version()

    return {
        'system_name': sys_ver.get('system_name', 'Clarity Retail: Gadgets store'),
        'system_short_name': sys_ver.get('short_name', 'Clarity Retail'),
        'system_version': sys_ver,
        'company_settings': settings_obj,
        'settings': settings_obj,  # backwards compatibility
        'unread_notifications': unread_notifications,
        'unread_notifications_count': unread_notifications_count,
        'low_stock_count': low_stock_count,
        'needs_mandatory_setup': needs_mandatory_setup,
        'mandatory_checklist': mandatory_checklist,
        'has_categories': has_categories,
        'has_suppliers': has_suppliers,
        'has_customers': has_customers,
        'has_expense_categories': has_expense_categories,
        'has_company_profile': has_company_profile,
    }


