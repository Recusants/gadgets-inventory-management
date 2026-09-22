from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Expenses Routes
    path('', views.expense_list_view, name='expense_list'),
    path('table/', views.expense_table_partial, name='expense_table'),
    path('add/', views.expense_add_modal, name='expense_add_modal'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/edit/', views.expense_edit_modal, name='expense_edit_modal'),
    path('<int:pk>/update/', views.expense_update, name='expense_update'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('<int:pk>/detail/', views.expense_detail_modal, name='expense_detail_modal'),

    # Expense Categories Table Routes
    path('categories/', views.expense_category_list_view, name='category_list'),
    path('categories/table/', views.expense_category_table_partial, name='category_table'),
    path('categories/add/', views.expense_category_add_modal, name='category_add_modal'),
    path('categories/create/', views.expense_category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.expense_category_edit_modal, name='category_edit_modal'),
    path('categories/<int:pk>/update/', views.expense_category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.expense_category_delete, name='category_delete'),
]
