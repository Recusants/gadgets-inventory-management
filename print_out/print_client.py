"""
Print Client for Gadget Store System.
Dispatches ESC/POS documents and thermal slip receipts to Windows Print Server via TCP socket.
"""

import json
import logging
import socket
from decimal import Decimal
from datetime import datetime

from .models import Printer

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def format_receipt_qty(qty):
    """Format quantity cleanly for thermal paper without unnecessary decimals."""
    if qty is None:
        return "1"
    try:
        dec = Decimal(str(qty))
        if dec == dec.to_integral():
            return str(int(dec))
        return f"{dec:f}".rstrip('0').rstrip('.')
    except Exception:
        return str(qty)


def send_to_print_server(server_ip, server_port, printer_name, print_type="document", document=None, text="", timeout=DEFAULT_TIMEOUT):
    """Send print payload over TCP socket to Windows print server."""
    payload = {
        "type": print_type,
        "printer_name": printer_name,
    }

    if print_type == "text":
        payload["text"] = text
    elif print_type == "document":
        if not isinstance(document, dict):
            return {"status": "error", "message": "Document must be a dictionary."}
        payload["document"] = document

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect((server_ip, int(server_port)))
        message = json.dumps(payload) + "\n"
        sock.sendall(message.encode("utf-8"))

        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in chunk:
                break

        if response_data:
            return json.loads(response_data.decode("utf-8").strip())
        return {"status": "error", "message": "Empty response from print server."}

    except socket.timeout:
        return {"status": "error", "message": f"Connection timed out ({server_ip}:{server_port})."}
    except ConnectionRefusedError:
        return {"status": "error", "message": f"Print server not running on {server_ip}:{server_port}."}
    except Exception as e:
        logger.exception("Error sending job to print server")
        return {"status": "error", "message": str(e)}
    finally:
        sock.close()


def print_document(printer, document):
    """Send a structured document dict to printer."""
    if not isinstance(document, dict):
        return {"status": "error", "message": "Document must be a dictionary."}
    document = dict(document)
    document["printer_name"] = printer.name

    return send_to_print_server(
        server_ip=printer.get_resolved_ip(),
        server_port=printer.server_port,
        printer_name=printer.name,
        print_type="document",
        document=document,
    )


def test_printer(printer):
    """Send a test slip to verify hardware connection, alignment, and paper cut."""
    paper_width = 80
    if hasattr(printer, 'paper_width') and '58' in str(printer.paper_width):
        paper_width = 58

    test_doc = {
        "type": "document",
        "printer_name": printer.name,
        "paper": {
            "width": paper_width,
            "cut": True,
            "copies": 1,
        },
        "content": [
            {
                "type": "text",
                "text": "================================================",
                "align": "center",
            },
            {
                "type": "text",
                "text": "HARDWARE TEST PRINT",
                "align": "center",
                "bold": True,
                "size": 1,
            },
            {
                "type": "text",
                "text": "================================================",
                "align": "center",
            },
            {
                "type": "text",
                "text": f"Printer : {printer.display_name or printer.name}\nHost    : {printer.server_ip}:{printer.server_port}\nPaper   : {printer.paper_width}\nDate    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nStatus  : Online & Ready\n",
                "align": "left",
            },
            {
                "type": "row",
                "columns": [
                    {"text": "Left Aligned", "align": "left", "width": 24},
                    {"text": "Right Aligned", "align": "right", "width": 24},
                ],
            },
            {
                "type": "text",
                "text": "\n------------------------------------------------\nThermal Print Engine Verified Successfully!\n------------------------------------------------\n\n",
                "align": "center",
            },
        ],
    }
    return print_document(printer, test_doc)


def get_printer(request=None):
    """Find default enabled unpaused printer, or fallback to any active printer."""
    # 1. Lookup default printer
    default_printer = Printer.objects.filter(enabled=True, is_paused=False, is_default=True).first()
    if default_printer:
        return default_printer

    # 2. Fallback: Any active, unpaused printer
    return Printer.objects.filter(enabled=True, is_paused=False).first()


def print_sale_receipt(printer, sale, is_copy=False):
    """
    Format and send a branded thermal receipt for a Gadget Store Sale.
    Includes item IMEI/serials, warranty info, customer details, and fiscal QR code.
    """
    from core.models import CompanySetting

    company_settings = CompanySetting.get_settings()
    company_name = company_settings.company_name or "GADGET STORE SYSTEM"
    store_address = company_settings.address or ""
    store_phone = company_settings.phone or ""
    store_email = company_settings.email or ""
    tagline = company_settings.tagline or "Quality Electronics & Mobile Accessories"

    paper_width_val = 80
    if hasattr(printer, 'paper_width') and '58' in str(printer.paper_width):
        paper_width_val = 58

    col_desc_width = 34 if paper_width_val >= 80 else 22
    col_price_width = 14 if paper_width_val >= 80 else 10

    copy_label = " (COPY)" if is_copy else ""
    header_title = f"TAX INVOICE / RECEIPT{copy_label}"

    content = [
        {
            "type": "text",
            "text": "------------------------------------------------",
            "align": "center",
        },
        {
            "type": "text",
            "text": company_name.upper(),
            "align": "center",
            "bold": True,
            "size": 1,
        },
        {
            "type": "text",
            "text": tagline,
            "align": "center",
        },
    ]

    contact_lines = []
    if store_address:
        contact_lines.append(store_address)
    if store_phone:
        contact_lines.append(f"Tel: {store_phone}")
    if store_email:
        contact_lines.append(f"Email: {store_email}")

    if contact_lines:
        content.append({
            "type": "text",
            "text": "\n".join(contact_lines),
            "align": "center",
        })

    content.append({
        "type": "text",
        "text": f"------------------------------------------------\n{header_title}\n------------------------------------------------",
        "align": "center",
        "bold": True,
    })

    # Metadata & Customer details
    date_str = sale.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(sale, 'created_at') and sale.created_at else datetime.now().strftime('%Y-%m-%d %H:%M')
    cashier_name = sale.user.get_full_name() or sale.user.username if sale.user else "Cashier"
    customer_name = sale.customer.name if sale.customer else "Walk-in Customer"
    customer_phone = sale.customer.phone if (sale.customer and sale.customer.phone) else ""

    meta_text = (
        f"Invoice #: {sale.invoice_number}\n"
        f"Date     : {date_str}\n"
        f"Cashier  : {cashier_name}\n"
        f"Customer : {customer_name}"
    )
    if customer_phone:
        meta_text += f"\nContact  : {customer_phone}"

    content.append({
        "type": "text",
        "text": meta_text + "\n------------------------------------------------",
        "align": "left",
    })

    # Items Header
    content.append({
        "type": "row",
        "columns": [
            {"text": "Qty Description", "align": "left", "bold": True, "width": col_desc_width},
            {"text": "Total ($)", "align": "right", "bold": True, "width": col_price_width},
        ],
    })
    content.append({
        "type": "text",
        "text": "------------------------------------------------",
        "align": "left",
    })

    # Line Items
    for item in sale.items.select_related('product').all():
        qty_str = format_receipt_qty(item.quantity)
        prod_title = item.product.name if item.product else "Item"
        line_desc = f"{qty_str} x {prod_title}"[:col_desc_width]
        line_total_str = f"${float(item.total_price):.2f}"

        content.append({
            "type": "row",
            "columns": [
                {"text": line_desc, "align": "left", "width": col_desc_width},
                {"text": line_total_str, "align": "right", "width": col_price_width},
            ],
        })

        # Serial number / IMEI tracking info
        serial_info = []
        if getattr(item, 'serial_number', None):
            serial_info.append(f"SN: {item.serial_number}")
        if getattr(item, 'imei_numbers', None):
            serial_info.append(f"IMEI: {item.imei_numbers}")
        if getattr(item, 'warranty_months', None) and item.warranty_months > 0:
            serial_info.append(f"Warranty: {item.warranty_months} Mo")

        if serial_info:
            content.append({
                "type": "text",
                "text": "  [" + " | ".join(serial_info) + "]",
                "align": "left",
            })

    content.append({
        "type": "text",
        "text": "------------------------------------------------",
        "align": "left",
    })

    # Totals & Payment Method
    tot_val = float(sale.total_amount)
    content.append({
        "type": "row",
        "columns": [
            {"text": "GRAND TOTAL:", "align": "left", "bold": True, "width": col_desc_width},
            {"text": f"${tot_val:.2f}", "align": "right", "bold": True, "width": col_price_width},
        ],
    })
    content.append({
        "type": "text",
        "text": f"Payment Method: {sale.get_payment_method_display() if hasattr(sale, 'get_payment_method_display') else sale.payment_method}\n================================================",
        "align": "left",
    })

    # ZIMRA Fiscalisation verification details (if present)
    try:
        from fiscalisation.models import FiscalReceipt
        fiscal_rec = FiscalReceipt.objects.filter(local_receipt_number=sale.id).first()
        if fiscal_rec:
            fiscal_text = (
                f"\n--- ZIMRA FISCAL DATA ---\n"
                f"Device ID : {fiscal_rec.device_id}\n"
                f"Fiscal Day: {fiscal_rec.fiscal_day}\n"
                f"Receipt # : {fiscal_rec.receipt_counter}\n"
                f"Global No : {fiscal_rec.receipt_global_no}\n"
            )
            content.append({
                "type": "text",
                "text": fiscal_text,
                "align": "center",
            })
            if fiscal_rec.verification_url:
                content.append({
                    "type": "qr",
                    "data": fiscal_rec.verification_url,
                    "align": "center",
                    "size": 4,
                })
    except Exception:
        pass

    content.append({
        "type": "text",
        "text": "\nThank you for your business!\nPlease retain this receipt for warranty claims.\n\n\n",
        "align": "center",
    })

    document = {
        "type": "document",
        "printer_name": printer.name,
        "paper": {
            "width": paper_width_val,
            "cut": True,
            "copies": 1,
        },
        "content": content,
    }

    return print_document(printer, document)
