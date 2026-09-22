from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_index_view, name='index'),
    path('export/sales/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('export/sales/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('export/inventory/excel/', views.export_inventory_excel, name='export_inventory_excel'),
    path('export/inventory/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
]
