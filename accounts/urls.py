from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Management (Admin Only)
    path('users/', views.user_list_view, name='user_list'),
    path('users/table/', views.user_table_partial, name='user_table'),
    path('users/add/', views.user_add_modal, name='user_add_modal'),
    path('users/<int:pk>/edit/', views.user_edit_modal, name='user_edit_modal'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
]
