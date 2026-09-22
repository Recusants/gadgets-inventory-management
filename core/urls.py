from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('test-modal/', views.test_modal, name='test_modal'),
    path('test-ajax/', views.test_ajax, name='test_ajax'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),

    # Notifications routes
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/table/', views.notification_table_partial, name='notification_table'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),

    # Database Backup & Restore Routes (Universal SQLite / Postgres / Docker)
    path('backup/download/', views.db_backup_download, name='backup_download'),
    path('backup/restore/', views.db_backup_restore, name='backup_restore'),
]
