from .models import CompanySetting, Notification
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

    return {
        'company_settings': settings_obj,
        'settings': settings_obj,  # backwards compatibility
        'unread_notifications': unread_notifications,
        'unread_notifications_count': unread_notifications_count,
        'low_stock_count': low_stock_count,
    }
