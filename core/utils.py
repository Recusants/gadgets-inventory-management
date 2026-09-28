"""Utility functions for system notifications and alerts."""
from django.db.models import F
from django.utils import timezone
from .models import Notification
from inventory.models import Stock, StockBatch

def sync_low_stock_notifications():
    """
    Scans all stock items and creates/updates low stock notifications
    based on the reorder_quantity threshold.
    """
    try:
        low_stocks = Stock.objects.filter(
            quantity_available__lte=F('reorder_quantity')
        ).select_related('product')

        for stock in low_stocks:
            p = stock.product
            title = f"Low Stock: {p.name}"
            
            # Determine severity
            if stock.quantity_available <= 0:
                severity = 'CRITICAL'
                msg = f"CRITICAL: {p.name} is completely out of stock (0 units remaining). Reorder threshold is {stock.reorder_quantity}."
            elif stock.quantity_available <= (stock.reorder_quantity / 2):
                severity = 'URGENT'
                msg = f"URGENT: {p.name} stock level is at {stock.quantity_available} units (critically below threshold of {stock.reorder_quantity})."
            else:
                severity = 'WARNING'
                msg = f"WARNING: {p.name} stock level is at {stock.quantity_available} units (reorder threshold is {stock.reorder_quantity})."

            link = f"/inventory/batches/"
            
            # Check if an unread notification exists
            existing = Notification.objects.filter(
                title=title,
                notification_type=Notification.NotificationType.LOW_STOCK,
                is_read=False
            ).first()
            if not existing:
                Notification.objects.create(
                    title=title,
                    message=msg,
                    notification_type=Notification.NotificationType.LOW_STOCK,
                    product=p,
                    severity=severity,
                    link_url=link,
                    is_read=False
                )
            else:
                # Update severity and product if changed
                if existing.severity != severity or existing.product != p or existing.message != msg:
                    existing.severity = severity
                    existing.product = p
                    existing.message = msg
                    existing.save(update_fields=['severity', 'product', 'message'])

        # Mark read for stocks that are now replenished above reorder_quantity
        replenished_stocks = Stock.objects.filter(
            quantity_available__gt=F('reorder_quantity')
        ).values_list('product__name', flat=True)

        for name in replenished_stocks:
            Notification.objects.filter(
                title=f"Low Stock: {name}",
                notification_type=Notification.NotificationType.LOW_STOCK,
                is_read=False
            ).update(is_read=True)

    except Exception:
        pass


def sync_expiry_notifications():
    """
    Scans active batches and generates adaptive expiration alerts.
    Considers total product shelf life to adapt the alert window (e.g. 60 days for 2-year shelf life,
    14-30 days for medium, 5 days for short shelf life), avoiding spam while remaining proactive.
    Updates notifications in-place so duplicate alerts are never created every day.
    """
    try:
        today = timezone.now().date()
        active_batches = StockBatch.objects.filter(
            is_active=True,
            quantity_remaining__gt=0,
            expiration_date__isnull=False
        ).select_related('product', 'stock')

        for b in active_batches:
            p = b.product
            days_rem = (b.expiration_date - today).days

            # Adaptive shelf-life threshold
            total_shelf_days = 365
            if b.date_received and b.expiration_date:
                total_shelf_days = max(1, (b.expiration_date - b.date_received).days)

            if total_shelf_days > 365:
                threshold = 60
            elif total_shelf_days >= 90:
                threshold = 30
            elif total_shelf_days >= 30:
                threshold = 14
            else:
                threshold = 5

            # Allow stock custom preference if explicitly set
            if hasattr(b, 'stock') and b.stock and b.stock.expiry_warning_days:
                if total_shelf_days >= 90:
                    threshold = max(threshold, b.stock.expiry_warning_days)
                else:
                    threshold = min(threshold, b.stock.expiry_warning_days)

            if days_rem <= threshold:
                if days_rem < 0:
                    severity = 'CRITICAL'
                    title = f"Expired: {p.name} (Batch #{b.id})"
                    msg = f"CRITICAL EXPIRED: Batch #{b.id} of '{p.name}' ({b.quantity_remaining} units) expired on {b.expiration_date.strftime('%Y-%m-%d')} ({abs(days_rem)} day(s) ago)."
                elif days_rem <= 7:
                    severity = 'URGENT' if days_rem > 3 else 'CRITICAL'
                    title = f"Urgent Expiry: {p.name} (Batch #{b.id})"
                    msg = f"URGENT: Batch #{b.id} of '{p.name}' ({b.quantity_remaining} units) expires in {days_rem} day(s) on {b.expiration_date.strftime('%Y-%m-%d')}."
                else:
                    severity = 'WARNING'
                    title = f"Expiring Soon: {p.name} (Batch #{b.id})"
                    msg = f"WARNING: Batch #{b.id} of '{p.name}' ({b.quantity_remaining} units) will expire on {b.expiration_date.strftime('%Y-%m-%d')} ({days_rem} days remaining)."

                existing = Notification.objects.filter(
                    batch=b,
                    notification_type=Notification.NotificationType.EXPIRING,
                    is_read=False
                ).first()

                if not existing:
                    Notification.objects.create(
                        title=title,
                        message=msg,
                        notification_type=Notification.NotificationType.EXPIRING,
                        product=p,
                        batch=b,
                        severity=severity,
                        link_url="/inventory/batches/",
                        is_read=False
                    )
                else:
                    if existing.title != title or existing.severity != severity or existing.message != msg:
                        existing.title = title
                        existing.severity = severity
                        existing.message = msg
                        existing.save(update_fields=['title', 'severity', 'message'])
            else:
                # If expiration date was changed or extended beyond threshold
                Notification.objects.filter(
                    batch=b,
                    notification_type=Notification.NotificationType.EXPIRING,
                    is_read=False
                ).update(is_read=True)

        # Mark read for batches that are now exhausted
        Notification.objects.filter(
            batch__quantity_remaining=0,
            notification_type=Notification.NotificationType.EXPIRING,
            is_read=False
        ).update(is_read=True)

    except Exception:
        pass


def sync_all_stock_notifications():
    """Sync both low-stock and expiry notifications."""
    sync_low_stock_notifications()
    sync_expiry_notifications()
