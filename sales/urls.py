from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales listing & table
    path('', views.sale_list_view, name='sale_list'),
    path('table/', views.sale_table_partial, name='sale_table'),
    path('add/', views.sale_add_modal, name='sale_add_modal'),
    path('<int:pk>/detail/', views.sale_detail_modal, name='sale_detail_modal'),
    path('create/', views.sale_create, name='sale_create'),
    path('<int:pk>/delete/', views.sale_delete, name='sale_delete'),

    # POS Checkout & PDF Receipt
    path('checkout/', views.pos_checkout_view, name='checkout'),
    path('<int:pk>/receipt/', views.receipt_pdf_view, name='receipt_pdf'),

    # Customer management routes
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/table/', views.customer_table_partial, name='customer_table'),
    path('customers/search/', views.customer_search_ajax, name='customer_search_ajax'),
    path('customers/add/', views.customer_add_modal, name='customer_add_modal'),
    path('customers/<int:pk>/edit/', views.customer_edit_modal, name='customer_edit_modal'),
    path('customers/<int:pk>/detail/', views.customer_detail_modal, name='customer_detail_modal'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/update/', views.customer_update, name='customer_update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
]
