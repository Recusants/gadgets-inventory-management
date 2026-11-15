"""
Views for Thermal Receipt Printers & POS Hardware Management.
"""

import json
import logging
import socket

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Printer
from .print_client import test_printer, print_document

logger = logging.getLogger(__name__)


def json_body(request):
    """Safely decode JSON request body."""
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return None


def printers_page(request):
    """Render Thermal Hardware & Printers configuration page."""
    printers = Printer.objects.all()
    return render(request, "print_out/printers_page.html", {
        "printers": printers,
        "active_menu": "printers",
    })


@require_GET
def printer_list(request):
    """Return JSON list of configured printers with connection status."""
    printers = Printer.objects.all()
    results = []
    for p in printers:
        results.append({
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name or p.name,
            "server_ip": p.server_ip,
            "server_port": p.server_port,
            "enabled": p.enabled,
            "is_paused": p.is_paused,
            "is_default": p.is_default,
            "paper_width": p.paper_width,
        })
    return JsonResponse({"status": "success", "printers": results})


@require_POST
def printer_add(request):
    """Add a new Windows thermal slip printer."""
    data = json_body(request)
    if not data:
        data = request.POST

    name = str(data.get("name", "")).strip()
    if not name:
        return JsonResponse({"status": "error", "message": "Printer name is required."}, status=400)

    display_name = str(data.get("display_name", "")).strip() or name
    server_ip = str(data.get("server_ip", "127.0.0.1")).strip() or "127.0.0.1"
    server_port = int(data.get("server_port", 9101))
    paper_width = str(data.get("paper_width", "80mm")).strip()
    is_default = bool(data.get("is_default", False))

    if Printer.objects.filter(name__iexact=name).exists():
        return JsonResponse({"status": "error", "message": f"Printer '{name}' is already registered."}, status=400)

    # First printer automatically defaults to default
    if not Printer.objects.filter(is_default=True).exists():
        is_default = True

    printer = Printer.objects.create(
        name=name,
        display_name=display_name,
        server_ip=server_ip,
        server_port=server_port,
        paper_width=paper_width,
        is_default=is_default,
        enabled=True,
    )

    return JsonResponse({
        "status": "success",
        "message": f"Printer '{printer.display_name}' added successfully.",
        "printer": {
            "id": printer.id,
            "name": printer.name,
            "display_name": printer.display_name,
            "is_default": printer.is_default,
        }
    })


@require_POST
def printer_update(request, printer_id):
    """Update printer configuration."""
    printer = get_object_or_404(Printer, pk=printer_id)
    data = json_body(request) or request.POST

    if "name" in data and data["name"].strip():
        printer.name = data["name"].strip()
    if "display_name" in data:
        printer.display_name = data["display_name"].strip()
    if "server_ip" in data and data["server_ip"].strip():
        printer.server_ip = data["server_ip"].strip()
    if "server_port" in data:
        try:
            printer.server_port = int(data["server_port"])
        except ValueError:
            pass
    if "paper_width" in data:
        printer.paper_width = data["paper_width"].strip()
    if "is_default" in data:
        printer.is_default = bool(data["is_default"])

    printer.save()
    return JsonResponse({
        "status": "success",
        "message": f"Printer '{printer.display_name}' updated successfully."
    })


@require_POST
def printer_delete(request, printer_id):
    """Delete a printer configuration."""
    printer = get_object_or_404(Printer, pk=printer_id)
    name = printer.display_name or printer.name
    printer.delete()
    return JsonResponse({
        "status": "success",
        "message": f"Printer '{name}' deleted successfully."
    })


@require_POST
def printer_toggle_pause(request, printer_id):
    """Toggle printer paused state."""
    printer = get_object_or_404(Printer, pk=printer_id)
    printer.is_paused = not printer.is_paused
    printer.save()
    return JsonResponse({
        "status": "success",
        "is_paused": printer.is_paused,
        "message": f"Printer {'paused' if printer.is_paused else 'resumed'}."
    })


@require_POST
def printer_toggle_active(request, printer_id):
    """Toggle printer enabled state."""
    printer = get_object_or_404(Printer, pk=printer_id)
    printer.enabled = not printer.enabled
    printer.save()
    return JsonResponse({
        "status": "success",
        "enabled": printer.enabled,
        "message": f"Printer {'enabled' if printer.enabled else 'disabled'}."
    })


@require_POST
def printer_set_default(request, printer_id):
    """Set printer as primary default."""
    printer = get_object_or_404(Printer, pk=printer_id)
    printer.is_default = True
    printer.save()
    return JsonResponse({
        "status": "success",
        "message": f"'{printer.display_name}' set as default printer."
    })


def printer_health(request, printer_id):
    """Check TCP connectivity to the Windows print server."""
    printer = get_object_or_404(Printer, pk=printer_id)
    resolved_ip = printer.get_resolved_ip()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    online = False
    error_msg = ""

    try:
        sock.connect((resolved_ip, int(printer.server_port)))
        online = True
    except Exception as e:
        error_msg = str(e)
    finally:
        sock.close()

    return JsonResponse({
        "status": "success",
        "printer_id": printer.id,
        "name": printer.name,
        "online": online,
        "resolved_ip": resolved_ip,
        "port": printer.server_port,
        "error": error_msg if not online else None,
    })


@require_POST
def printer_test(request, printer_id):
    """Send test receipt to physical hardware."""
    printer = get_object_or_404(Printer, pk=printer_id)
    result = test_printer(printer)
    if result.get("status") == "success":
        return JsonResponse({
            "status": "success",
            "message": f"Test slip sent to '{printer.display_name}' successfully!"
        })
    return JsonResponse({
        "status": "error",
        "message": result.get("message", "Test print failed. Ensure print server is running.")
    }, status=500)
