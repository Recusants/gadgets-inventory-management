from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Product routes
    path('products/', views.product_list_view, name='product_list'),
    path('products/table/', views.product_table_partial, name='product_table'),
    path('products/search/', views.product_search_ajax, name='product_search_ajax'),
    path('products/add/', views.product_add_modal, name='product_add_modal'),
    path('products/<int:pk>/edit/', views.product_edit_modal, name='product_edit_modal'),
    path('products/<int:pk>/detail/', views.product_detail_modal, name='product_detail_modal'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Receive Invoice / Stock Intake routes
    path('receive-invoice/', views.receive_invoice_modal, name='receive_invoice_modal'),
    path('receive-invoice/save/', views.receive_invoice_save, name='receive_invoice_save'),
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('invoices/table/', views.invoice_table_partial, name='invoice_table'),
    path('invoices/<str:invoice_number>/detail/', views.invoice_detail_modal, name='invoice_detail_modal'),

    # Dedicated Stock (Pricing & Valuation) routes
    path('stock/', views.stock_list_view, name='stock_list'),
    path('stock/table/', views.stock_table_partial, name='stock_table'),
    path('stock/<int:pk>/price/modal/', views.stock_price_modal, name='stock_price_modal'),
    path('stock/<int:pk>/price/update/', views.stock_price_update, name='stock_price_update'),

    # Batches routes (details and edit quantities)
    path('batches/', views.batch_list_view, name='batch_list'),
    path('batches/<int:pk>/detail/', views.batch_detail_modal, name='batch_detail_modal'),
    path('batches/<int:pk>/edit-quantity/', views.batch_quantity_edit_modal, name='batch_quantity_edit_modal'),
    path('batches/<int:pk>/update-quantity/', views.batch_quantity_update, name='batch_quantity_update'),


    # Category routes
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/table/', views.category_table_partial, name='category_table'),
    path('categories/add/', views.category_add_modal, name='category_add_modal'),
    path('categories/<int:pk>/edit/', views.category_edit_modal, name='category_edit_modal'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Supplier routes
    path('suppliers/', views.supplier_list_view, name='supplier_list'),
    path('suppliers/table/', views.supplier_table_partial, name='supplier_table'),
    path('suppliers/add/', views.supplier_add_modal, name='supplier_add_modal'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit_modal, name='supplier_edit_modal'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
]
