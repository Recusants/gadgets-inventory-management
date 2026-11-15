"""
URL configuration for 21 Void Technologies.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('reports/', include('reports.urls')),
    path('core/', include('core.urls')),
    path('api/search-features/', core_views.load_all_search_features, name='load_all_search_features'),
    path('load_all_search_features/', core_views.load_all_search_features),
    path('notifications/', core_views.notification_list_view, name='notifications_direct'),
    path('settings/', core_views.settings_view, name='settings_direct'),
    path('system/', core_views.system_view, name='system_direct'),
    path('whats-new/', core_views.whats_new_view, name='whats_new_direct'),
    path('expenses/', include('expenses.urls')),
    path('fiscalisation/', include('fiscalisation.urls')),
    path('printers/', include('print_out.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
