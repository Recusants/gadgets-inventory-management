"""
Tests for POS Hardware & Thermal Printer management.
"""

import json
import socket
from django.test import TestCase, Client
from .models import Printer
from .print_client import get_printer, format_receipt_qty
from accounts.models import User, UserRole
from sales.models import Sale, PaymentMethod


class PrinterModelTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="manager1",
            email="manager1@example.com",
            password="Password123!",
            roles=[UserRole.MANAGER]
        )

    def test_printer_creation_and_default_enforcement(self):
        p1 = Printer.objects.create(name="POS-80", display_name="Counter 1", is_default=True)
        self.assertTrue(p1.is_default)

        # Creating a second default printer should un-default the first
        p2 = Printer.objects.create(name="POS-90", display_name="Counter 2", is_default=True)
        p1.refresh_from_db()
        self.assertFalse(p1.is_default)
        self.assertTrue(p2.is_default)

    def test_get_resolved_ip_loopback(self):
        p = Printer.objects.create(name="TEST-POS", server_ip="127.0.0.1")
        resolved = p.get_resolved_ip()
        self.assertTrue(bool(resolved))
        # Verify it resolves to a valid IPv4 address or hostname
        try:
            socket.inet_aton(resolved)
            is_valid_ip = True
        except socket.error:
            is_valid_ip = (resolved in ["127.0.0.1", "host.docker.internal"])
        self.assertTrue(is_valid_ip)

    def test_format_receipt_qty(self):
        self.assertEqual(format_receipt_qty(1), "1")
        self.assertEqual(format_receipt_qty(2.0), "2")
        self.assertEqual(format_receipt_qty(2.5), "2.5")

    def test_get_printer_fallback(self):
        self.assertIsNone(get_printer())

        p1 = Printer.objects.create(name="P1", enabled=True, is_paused=True, is_default=True)
        # Paused printer should not be returned
        self.assertIsNone(get_printer())

        p2 = Printer.objects.create(name="P2", enabled=True, is_paused=False, is_default=False)
        self.assertEqual(get_printer(), p2)

    def test_printer_api_list_and_add(self):
        self.client.force_login(self.user)
        res = self.client.get('/printers/api/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')

        add_res = self.client.post(
            '/printers/api/add/',
            json.dumps({"name": "POS-EPSON", "display_name": "Epson TM-T20", "paper_width": "80mm"}),
            content_type="application/json"
        )
        self.assertEqual(add_res.status_code, 200)
        self.assertTrue(Printer.objects.filter(name="POS-EPSON").exists())

    def test_printer_toggle_pause_and_default(self):
        self.client.force_login(self.user)
        p = Printer.objects.create(name="P-TOGGLE", enabled=True, is_paused=False)

        pause_res = self.client.post(f'/printers/api/{p.id}/toggle-pause/')
        self.assertEqual(pause_res.status_code, 200)
        p.refresh_from_db()
        self.assertTrue(p.is_paused)

        def_res = self.client.post(f'/printers/api/{p.id}/default/')
        self.assertEqual(def_res.status_code, 200)
        p.refresh_from_db()
        self.assertTrue(p.is_default)
