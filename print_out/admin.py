from django.contrib import admin
from .models import Printer


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "server_ip", "server_port", "paper_width", "enabled", "is_paused", "is_default")
    list_filter = ("enabled", "is_paused", "is_default", "paper_width")
    search_fields = ("name", "display_name", "server_ip")
