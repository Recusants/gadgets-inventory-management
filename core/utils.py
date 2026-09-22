"""Utility functions for system notifications and alerts."""
from django.db.models import F
from .models import Notification
from inventory.models import Stock

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
                if existing.severity != severity or existing.product != p:
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
