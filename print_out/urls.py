from django.urls import path
from . import views

app_name = "print_out"

urlpatterns = [
    path("", views.printers_page, name="printers_page"),
    path("api/", views.printer_list, name="printer_list"),
    path("api/add/", views.printer_add, name="printer_add"),
    path("api/<int:printer_id>/update/", views.printer_update, name="printer_update"),
    path("api/<int:printer_id>/delete/", views.printer_delete, name="printer_delete"),
    path("api/<int:printer_id>/toggle-pause/", views.printer_toggle_pause, name="printer_toggle_pause"),
    path("api/<int:printer_id>/toggle-active/", views.printer_toggle_active, name="printer_toggle_active"),
    path("api/<int:printer_id>/default/", views.printer_set_default, name="printer_set_default"),
    path("api/<int:printer_id>/health/", views.printer_health, name="printer_health"),
    path("api/<int:printer_id>/test/", views.printer_test, name="printer_test"),
]
