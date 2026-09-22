from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Sale, SaleItem

@receiver(post_save, sender=Sale)
def on_sale_saved(sender, instance, created, **kwargs):
    """Invalidate dashboard cached aggregations on sale create/update."""
    cache.delete('dashboard_stats')

@receiver(post_delete, sender=Sale)
def on_sale_deleted(sender, instance, **kwargs):
    """Invalidate dashboard cached aggregations on sale delete."""
    cache.delete('dashboard_stats')

@receiver(post_save, sender=SaleItem)
def on_sale_item_saved(sender, instance, created, **kwargs):
    """Invalidate dashboard cached aggregations on sale item save."""
    cache.delete('dashboard_stats')
