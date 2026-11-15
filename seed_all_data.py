"""
Unified Comprehensive Seeding Script for Gadget Store System.
Seeds realistic, production-ready demo data across all tables and modules:
- Superuser: root@gmail.com (password: toor)
- Staff Roles: Admin, Manager, Supervisor, Cashier
- Company Settings & Print Configurations
- Thermal Printers (POS-80 Default, POS-58 Mobile)
- Fiscalisation Settings & Sample Fiscal Receipts
- Suppliers & Hardware Categories
- Master Products, Stocks, and FIFO StockBatches
- Customers (Walk-in + Individuals & Corporates)
- Completed Historical & Current POS Sales with FIFO Deductions
- Expense Categories & Realistic Expenses
- System & Low Stock Notifications

Supports multiple database targets via --settings (e.g. config.settings.local, config.settings.docker_dev, config.settings.env_dev).
"""

import os
import sys
import argparse
from decimal import Decimal
from datetime import date, timedelta

# 1. Parse settings argument before django.setup()
parser = argparse.ArgumentParser(description="Seed Gadget Store System with comprehensive realistic data.")
parser.add_argument("--settings", default=None, help="Django settings module path (e.g. config.settings.local)")
parser.add_argument("--clean", action="store_true", help="Clean existing transactional data before re-seeding")
args, unknown = parser.parse_known_args()

if args.settings:
    os.environ['DJANGO_SETTINGS_MODULE'] = args.settings
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

import django
django.setup()

from django.db import transaction
from django.utils import timezone
from accounts.models import User, UserRole
from core.models import CompanySetting, Notification
from inventory.models import Category, Product, Supplier, Stock, StockBatch
from sales.models import Customer, Sale, SaleItem, SaleBatchDeduction, PaymentMethod
from expenses.models import ExpenseCategory, Expense
from fiscalisation.models import FiscalisationSettings, FiscalReceiptSequence, FiscalReceipt
from print_out.models import Printer


def run_seed():
    print(f"============================================================")
    print(f"  SEEDING GADGET STORE SYSTEM")
    print(f"  Settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"============================================================")

    # -------------------------------------------------------------------------
    # 1. USER ACCOUNTS & CREDENTIALS
    # -------------------------------------------------------------------------
    print("\n[1/11] Seeding User Accounts...")

    # Root Superuser (root@gmail.com / toor)
    root_user, created = User.objects.get_or_create(
        username="root",
        defaults={
            "email": "root@gmail.com",
            "first_name": "System",
            "last_name": "Superuser",
            "roles": [UserRole.ADMIN],
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "phone": "+263 77 100 0001",
        }
    )
    root_user.email = "root@gmail.com"
    root_user.set_password("toor")
    root_user.roles = [UserRole.ADMIN]
    root_user.is_staff = True
    root_user.is_superuser = True
    root_user.is_active = True
    root_user.save()
    print(f"  ✓ Root Superuser: root@gmail.com (Password: toor) [Superuser: {root_user.is_superuser}]")

    # Primary Admin (James Zvokureva)
    admin_user, _ = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@21void.com",
            "first_name": "James",
            "last_name": "Zvokureva",
            "roles": [UserRole.ADMIN],
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "phone": "+263 77 123 4567",
        }
    )
    admin_user.email = "admin@21void.com"
    admin_user.set_password("Admin@21Void2026")
    admin_user.roles = [UserRole.ADMIN]
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_active = True
    admin_user.save()
    print(f"  ✓ Admin User: admin@21void.com (Password: Admin@21Void2026)")

    # Store Manager
    manager_user, _ = User.objects.get_or_create(
        username="manager",
        defaults={
            "email": "manager@21void.com",
            "first_name": "Tinashe",
            "last_name": "Mutasa",
            "roles": [UserRole.MANAGER],
            "is_staff": True,
            "is_superuser": False,
            "is_active": True,
            "phone": "+263 77 234 5678",
        }
    )
    manager_user.email = "manager@21void.com"
    manager_user.set_password("Manager@21Void2026")
    manager_user.roles = [UserRole.MANAGER]
    manager_user.is_staff = True
    manager_user.is_superuser = False
    manager_user.is_active = True
    manager_user.save()
    print(f"  ✓ Manager User: manager@21void.com (Password: Manager@21Void2026)")

    # Shift Supervisor
    supervisor_user, _ = User.objects.get_or_create(
        username="supervisor",
        defaults={
            "email": "supervisor@21void.com",
            "first_name": "Nyasha",
            "last_name": "Gumbo",
            "roles": [UserRole.SUPERVISOR],
            "is_staff": False,
            "is_superuser": False,
            "is_active": True,
            "phone": "+263 77 345 6789",
        }
    )
    supervisor_user.email = "supervisor@21void.com"
    supervisor_user.set_password("Supervisor@21Void2026")
    supervisor_user.roles = [UserRole.SUPERVISOR]
    supervisor_user.is_staff = False
    supervisor_user.is_superuser = False
    supervisor_user.is_active = True
    supervisor_user.save()
    print(f"  ✓ Supervisor User: supervisor@21void.com (Password: Supervisor@21Void2026)")

    # POS Cashier
    cashier_user, _ = User.objects.get_or_create(
        username="cashier",
        defaults={
            "email": "cashier@21void.com",
            "first_name": "Chipo",
            "last_name": "Dube",
            "roles": [UserRole.CASHIER],
            "is_staff": False,
            "is_superuser": False,
            "is_active": True,
            "phone": "+263 77 456 7890",
        }
    )
    cashier_user.email = "cashier@21void.com"
    cashier_user.set_password("Cashier@21Void2026")
    cashier_user.roles = [UserRole.CASHIER]
    cashier_user.is_staff = False
    cashier_user.is_superuser = False
    cashier_user.is_active = True
    cashier_user.save()
    print(f"  ✓ Cashier User: cashier@21void.com (Password: Cashier@21Void2026)")

    # -------------------------------------------------------------------------
    # 2. COMPANY SETTINGS
    # -------------------------------------------------------------------------
    print("\n[2/11] Seeding Company Settings...")
    comp = CompanySetting.get_settings()
    comp.company_name = "21 Void Technologies - Gadget Store"
    comp.tagline = "Premium Gadgets, Satellite Connectivity & Smart Power"
    comp.phone = "+263 77 123 4567"
    comp.email = "info@21void.com"
    comp.address = "Shop 4B, Celestial Mall, Samora Machel Ave, Harare, Zimbabwe"
    comp.currency_symbol = "$"
    comp.currency_code = "USD"
    comp.receipt_header_note = "Official Purchase Receipt - Tax Invoice"
    comp.receipt_footer_note = "Thank you for shopping with 21 Void Technologies! All electronic devices carry a manufacturer warranty. Returns accepted within 7 days with original receipt and packaging."
    comp.is_customized = True
    comp.save()
    print(f"  ✓ Company Settings saved: {comp.company_name}")

    # -------------------------------------------------------------------------
    # 3. THERMAL PRINTER HARDWARE
    # -------------------------------------------------------------------------
    print("\n[3/11] Seeding POS Printers...")
    p1, _ = Printer.objects.get_or_create(
        name="POS-80",
        defaults={
            "display_name": "Counter 1 Slip Printer (80mm)",
            "server_ip": "127.0.0.1",
            "server_port": 9101,
            "enabled": True,
            "is_default": True,
            "paper_width": "80mm",
        }
    )
    p1.display_name = "Counter 1 Slip Printer (80mm)"
    p1.server_ip = "127.0.0.1"
    p1.server_port = 9101
    p1.enabled = True
    p1.is_default = True
    p1.paper_width = "80mm"
    p1.save()

    p2, _ = Printer.objects.get_or_create(
        name="POS-58",
        defaults={
            "display_name": "Mobile Bluetooth Slip Printer (58mm)",
            "server_ip": "127.0.0.1",
            "server_port": 9101,
            "enabled": True,
            "is_default": False,
            "paper_width": "58mm",
        }
    )
    p2.display_name = "Mobile Bluetooth Slip Printer (58mm)"
    p2.server_ip = "127.0.0.1"
    p2.server_port = 9101
    p2.enabled = True
    p2.is_default = False
    p2.paper_width = "58mm"
    p2.save()
    print(f"  ✓ Thermal Printers: POS-80 (Default), POS-58")

    # -------------------------------------------------------------------------
    # 4. FISCALISATION SETTINGS & SEQUENCE
    # -------------------------------------------------------------------------
    print("\n[4/11] Seeding Fiscalisation Settings & Sequences...")
    fisc = FiscalisationSettings.get_settings()
    fisc.fiscalisation_enabled = False  # Ready with demo config
    fisc.api_base_url = "https://Zimratest.samcima.com/api/Zimra"
    fisc.qr_url = "https://fdmstest.zimra.co.zw"
    fisc.device_id = "TEST-DEV-GADGET-01"
    fisc.machine_code = "MACH-01"
    fisc.api_password = "ZimraDevPass2026"
    fisc.default_hs_code = "85171300"
    fisc.admin_email = "root@gmail.com"
    fisc.admin_phone = "+263 77 100 0001"
    fisc.save()

    seq, _ = FiscalReceiptSequence.objects.get_or_create(id=1)
    seq.fiscal_receipt_number = 12
    seq.fiscal_receipt_global_no = 145
    seq.last_fiscal_day = timezone.now().date()
    seq.save()
    print(f"  ✓ Fiscal Settings & Receipt Sequence #{seq.fiscal_receipt_global_no}")

    # -------------------------------------------------------------------------
    # 5. HARDWARE SUPPLIERS
    # -------------------------------------------------------------------------
    print("\n[5/11] Seeding Suppliers...")
    suppliers_data = [
        ("Apple Authorized Distributor", "John Miller", "+263 24 270 1100", "procurement@appledistrib.co.zw", "Borrowdale Commercial Centre, Harare", "Official Apple hardware distributor"),
        ("Samsung Electronics Southern Africa", "Amanda Sithole", "+263 24 288 2233", "orders@samsungsa.co.zw", "Sam Levy Village, Harare", "Regional Samsung distributor"),
        ("Starlink Direct Distribution", "Elon M.", "+1 310 363 6000", "orders@starlinkdistribution.com", "Hawthorne, California, USA", "Direct satellite hardware importer"),
        ("Ruijie Networks Regional Supply", "Kevin Chen", "+263 77 999 8888", "sales@ruijieafrica.com", "Graniteside Industrial, Harare", "Commercial enterprise networking gear"),
        ("Anker Innovations Africa", "David Dube", "+263 77 444 3322", "sales@anker-africa.com", "Msasa Business Park, Harare", "Premium charging and power bank distributor"),
        ("JBL & Harman Audio SA", "Lerato Khumalo", "+27 11 450 7800", "orders@harman-sa.co.za", "Sandton, Johannesburg, RSA", "Original JBL speakers and headphones"),
        ("Cudy Technologies Hub", "Alan Vance", "+263 78 111 2233", "support@cudy-distrib.com", "CBD, Harare", "Wi-Fi routers, switches and network adapters"),
    ]
    supplier_objs = {}
    for name, contact, phone, email, addr, notes in suppliers_data:
        supp, _ = Supplier.objects.get_or_create(
            name=name,
            defaults={
                "contact_person": contact,
                "phone": phone,
                "email": email,
                "address": addr,
                "notes": notes,
            }
        )
        supp.contact_person = contact
        supp.phone = phone
        supp.email = email
        supp.address = addr
        supp.notes = notes
        supp.save()
        supplier_objs[name] = supp
    print(f"  ✓ {len(supplier_objs)} Suppliers created/updated")

    # -------------------------------------------------------------------------
    # 6. PRODUCT CATEGORIES
    # -------------------------------------------------------------------------
    print("\n[6/11] Seeding Hardware Categories...")
    categories_data = [
        ("Satellite & Internet Equipment", "Starlink kits, high-performance satellite terminals, and networking gear"),
        ("Smartphones & Tablets", "Flagship iPhones, Samsung Galaxy devices, iPads, and Android tablets"),
        ("Laptops & Computing", "MacBooks, ultrabooks, portable workstations, and monitors"),
        ("Networking & Wi-Fi", "Dual-band and Wi-Fi 6 routers, access points, mesh systems, and PoE switches"),
        ("Power Solutions & Charging", "GaN chargers, heavy-duty power banks, solar inverters, and backup batteries"),
        ("Audio & Wearables", "Wireless headphones, noise-canceling earbuds, portable speakers, and smartwatches"),
        ("Accessories & Cables", "Screen protectors, MagSafe cases, USB-C thunderbolt cables, adapters"),
    ]
    cat_objs = {}
    for name, desc in categories_data:
        cat, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
        cat.description = desc
        cat.save()
        cat_objs[name] = cat
    print(f"  ✓ {len(cat_objs)} Categories created/updated")

    # -------------------------------------------------------------------------
    # 7. CUSTOMERS
    # -------------------------------------------------------------------------
    print("\n[7/11] Seeding Customers...")
    default_cust = Customer.get_default_customer()
    customers_data = [
        ("Farai Mutandwa", "+263 77 211 4455", "farai.m@gmail.com", "14 Borrowdale Brooke, Harare"),
        ("Kudzai Chisamba", "+263 77 355 6677", "kudzai.c@outlook.com", "28 Mount Pleasant Drive, Harare"),
        ("Sarah Van Wyk", "+263 71 488 9900", "sarah.vw@gmail.com", "Avondale West, Harare"),
        ("Tariro Zimuto", "+263 77 622 3344", "tariro.zimuto@econet.co.zw", "Newlands, Harare"),
        ("Delta Mining Supplies (Pvt) Ltd", "+263 24 278 9901", "procurement@deltamining.co.zw", "Southerton Industrial Park, Harare"),
        ("Apex Logistics Zimbabwe", "+263 77 899 1122", "operations@apexlogistics.co.zw", "Msasa Commercial Estate, Harare"),
        ("Tawanda Moyo", "+263 77 412 3456", "tawanda.moyo@gmail.com", "Greendale, Harare"),
        ("Chipo Makoni", "+263 77 987 6543", "chipo.makoni@yahoo.com", "Highlands, Harare"),
        ("Takudzwa Sithole", "+263 73 344 5566", "takudzwa.s@hotmail.com", "Belgravia, Harare"),
    ]
    customer_objs = {"Walk-in Customer": default_cust}
    for name, phone, email, addr in customers_data:
        cust, _ = Customer.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "email": email, "address": addr, "created_by": admin_user}
        )
        cust.name = name
        cust.email = email
        cust.address = addr
        cust.save()
        customer_objs[name] = cust
    print(f"  ✓ {len(customer_objs)} Customers created/updated")

    # -------------------------------------------------------------------------
    # 8. PRODUCTS, STOCK & FIFO STOCK BATCHES
    # -------------------------------------------------------------------------
    print("\n[8/11] Seeding Master Products, Stocks, and FIFO Batches...")

    # (Name, CatName, SKU, Size, Cost, Sell, ReorderQty, SupplierName, BatchesList)
    # BatchesList = [(InvNum, QtyRec, QtyRem, CostPrice, DaysAgoReceived, SerialNumber, Email)]
    today = timezone.now().date()

    products_spec = [
        # 1. Starlink Mini
        (
            "Starlink Mini Kit",
            "Satellite & Internet Equipment",
            "SL-MINI-01",
            "Ultra Portable DC Kit",
            Decimal("290.00"), Decimal("380.00"), 3,
            "Starlink Direct Distribution",
            [
                ("INV-SL-2026-081", 5, 3, Decimal("290.00"), 20, "SLM-2026-90123", "starlink.acc1@21void.com"),
                ("INV-SL-2026-095", 6, 6, Decimal("295.00"), 5, "", ""),
            ]
        ),
        # 2. Starlink Standard Gen 3
        (
            "Starlink Standard Kit Gen 3",
            "Satellite & Internet Equipment",
            "SL-GEN3-ACT",
            "Standard Kit with Wi-Fi 6 Router",
            Decimal("340.00"), Decimal("450.00"), 4,
            "Starlink Direct Distribution",
            [
                ("INV-SL-2026-077", 10, 8, Decimal("340.00"), 25, "SL3-2026-88192", "starlink.gen3@21void.com"),
                ("INV-SL-2026-099", 5, 5, Decimal("345.00"), 3, "", ""),
            ]
        ),
        # 3. iPhone 15 Pro Max
        (
            "iPhone 15 Pro Max 256GB",
            "Smartphones & Tablets",
            "APL-IP15PM-256",
            "256GB Natural Titanium",
            Decimal("1050.00"), Decimal("1280.00"), 3,
            "Apple Authorized Distributor",
            [
                ("INV-APL-4491", 4, 2, Decimal("1050.00"), 18, "IMEI-354892109823412", ""),
                ("INV-APL-4512", 4, 4, Decimal("1060.00"), 4, "IMEI-354892109823413", ""),
            ]
        ),
        # 4. iPhone 15
        (
            "iPhone 15 128GB",
            "Smartphones & Tablets",
            "APL-IP15-128",
            "128GB Black Edition",
            Decimal("720.00"), Decimal("880.00"), 4,
            "Apple Authorized Distributor",
            [
                ("INV-APL-4488", 8, 6, Decimal("720.00"), 22, "", ""),
                ("INV-APL-4515", 5, 5, Decimal("725.00"), 6, "", ""),
            ]
        ),
        # 5. Samsung Galaxy S24 Ultra
        (
            "Samsung Galaxy S24 Ultra 512GB",
            "Smartphones & Tablets",
            "SAM-S24U-512",
            "512GB Titanium Gray",
            Decimal("1100.00"), Decimal("1350.00"), 3,
            "Samsung Electronics Southern Africa",
            [
                ("INV-SAM-8812", 4, 3, Decimal("1100.00"), 15, "IMEI-990001122334455", ""),
                ("INV-SAM-8840", 3, 3, Decimal("1110.00"), 2, "", ""),
            ]
        ),
        # 6. Samsung Galaxy A55 5G
        (
            "Samsung Galaxy A55 5G 128GB",
            "Smartphones & Tablets",
            "SAM-A55-128",
            "128GB Awesome Navy",
            Decimal("280.00"), Decimal("360.00"), 5,
            "Samsung Electronics Southern Africa",
            [
                ("INV-SAM-8805", 15, 12, Decimal("280.00"), 30, "", ""),
            ]
        ),
        # 7. MacBook Air M3
        (
            "Apple MacBook Air M3 13\" 16GB/512GB",
            "Laptops & Computing",
            "APL-MBA-M3-13",
            "13.6-inch Midnight M3 Chip",
            Decimal("1180.00"), Decimal("1450.00"), 2,
            "Apple Authorized Distributor",
            [
                ("INV-APL-4475", 3, 2, Decimal("1180.00"), 14, "SN-C02GF892MD6M", ""),
                ("INV-APL-4520", 2, 2, Decimal("1190.00"), 1, "", ""),
            ]
        ),
        # 8. Dell XPS 15
        (
            "Dell XPS 15 9530 Core i7 / 32GB RAM / 1TB SSD",
            "Laptops & Computing",
            "DEL-XPS15-9530",
            "15.6-inch OLED 3.5K Touch",
            Decimal("1400.00"), Decimal("1750.00"), 2,
            "Ruijie Networks Regional Supply",
            [
                ("INV-DEL-3390", 3, 2, Decimal("1400.00"), 28, "SN-DELL-9530-XYZ", ""),
            ]
        ),
        # 9. Ruijie Reyee RG-EW3200GX PRO
        (
            "Ruijie Reyee RG-EW3200GX PRO Wi-Fi 6 Router",
            "Networking & Wi-Fi",
            "RJ-EW3200-PRO",
            "AX3200 Gigabit Mesh 8 Antennas",
            Decimal("115.00"), Decimal("165.00"), 5,
            "Ruijie Networks Regional Supply",
            [
                ("INV-RJ-7741", 20, 16, Decimal("115.00"), 25, "", ""),
            ]
        ),
        # 10. Ruijie Reyee RG-RAP62620D Outdoor AP
        (
            "Ruijie Reyee RG-RAP62620D Outdoor Access Point",
            "Networking & Wi-Fi",
            "RJ-RAP62620D",
            "Omni-directional Wi-Fi 6 Gigabit",
            Decimal("160.00"), Decimal("220.00"), 3,
            "Ruijie Networks Regional Supply",
            [
                ("INV-RJ-7755", 8, 6, Decimal("160.00"), 19, "", ""),
            ]
        ),
        # 11. Cudy AX3000 Router
        (
            "Cudy AX3000 Gigabit Wi-Fi 6 Router (WR3000)",
            "Networking & Wi-Fi",
            "CDY-WR3000",
            "AX3000 Dual Band 4x5dBi Antennas",
            Decimal("65.00"), Decimal("95.00"), 6,
            "Cudy Technologies Hub",
            [
                ("INV-CDY-1090", 25, 20, Decimal("65.00"), 21, "", ""),
            ]
        ),
        # 12. Anker 737 Power Bank
        (
            "Anker 737 Power Bank (PowerCore 24K 140W)",
            "Power Solutions & Charging",
            "ANK-737-24K",
            "24,000mAh 140W Smart Digital Display",
            Decimal("110.00"), Decimal("160.00"), 4,
            "Anker Innovations Africa",
            [
                ("INV-ANK-9912", 14, 10, Decimal("110.00"), 12, "", ""),
            ]
        ),
        # 13. Anker Prime 67W GaN Charger
        (
            "Anker Prime 67W 3-Port GaN Wall Charger",
            "Power Solutions & Charging",
            "ANK-PRIME-67W",
            "2x USB-C + 1x USB-A Foldable",
            Decimal("42.00"), Decimal("65.00"), 8,
            "Anker Innovations Africa",
            [
                ("INV-ANK-9920", 30, 24, Decimal("42.00"), 10, "", ""),
            ]
        ),
        # 14. Ecoflow River 2 Max
        (
            "Ecoflow River 2 Max 512Wh Portable Power Station",
            "Power Solutions & Charging",
            "ECO-RIV2-MAX",
            "512Wh LiFePO4 500W AC Inverter",
            Decimal("420.00"), Decimal("550.00"), 2,
            "Anker Innovations Africa",
            [
                ("INV-ECO-4401", 4, 3, Decimal("420.00"), 16, "", ""),
            ]
        ),
        # 15. JBL Charge 5
        (
            "JBL Charge 5 Portable Waterproof Bluetooth Speaker",
            "Audio & Wearables",
            "JBL-CHG5-BLK",
            "Squad Black Edition IP67",
            Decimal("125.00"), Decimal("175.00"), 4,
            "JBL & Harman Audio SA",
            [
                ("INV-JBL-2210", 12, 9, Decimal("125.00"), 14, "", ""),
            ]
        ),
        # 16. Sony WH-1000XM5
        (
            "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
            "Audio & Wearables",
            "SNY-WH1000-XM5",
            "Silver Over-ear with Auto NC Optimizer",
            Decimal("290.00"), Decimal("380.00"), 3,
            "JBL & Harman Audio SA",
            [
                ("INV-SNY-5510", 7, 5, Decimal("290.00"), 11, "", ""),
            ]
        ),
        # 17. Apple Watch Series 9
        (
            "Apple Watch Series 9 GPS 45mm",
            "Audio & Wearables",
            "APL-AW9-45",
            "Midnight Aluminum Case Sport Band",
            Decimal("340.00"), Decimal("430.00"), 3,
            "Apple Authorized Distributor",
            [
                ("INV-APL-4505", 6, 4, Decimal("340.00"), 17, "", ""),
            ]
        ),
        # 18. Baseus 100W USB-C Cable
        (
            "Baseus 100W 2M USB-C to USB-C Fast Charge Cable",
            "Accessories & Cables",
            "BAS-USBC-100W",
            "2 Metres Braided Cable with E-Marker",
            Decimal("6.00"), Decimal("15.00"), 10,
            "Anker Innovations Africa",
            [
                ("INV-BAS-6620", 50, 42, Decimal("6.00"), 30, "", ""),
            ]
        ),
        # 19. Starlink Ethernet Adapter V2 (Low Stock Item)
        (
            "Starlink Ethernet Adapter V2",
            "Accessories & Cables",
            "SL-ETH-ADP-V2",
            "RJ45 Gigabit Adapter for Gen 2 / Mini",
            Decimal("45.00"), Decimal("70.00"), 5,
            "Starlink Direct Distribution",
            [
                ("INV-SL-2026-065", 10, 2, Decimal("45.00"), 40, "", ""),  # 2 remaining <= 5 reorder threshold
            ]
        ),
        # 20. Apple 20W USB-C Power Adapter (Out of Stock Item)
        (
            "Apple 20W USB-C Power Adapter",
            "Power Solutions & Charging",
            "APL-20W-USBC",
            "Original UK Pin 3-Pin Charger",
            Decimal("18.00"), Decimal("28.00"), 5,
            "Apple Authorized Distributor",
            [
                ("INV-APL-4450", 15, 0, Decimal("18.00"), 45, "", ""),  # 0 remaining (Exhausted batch)
            ]
        ),
    ]

    product_objs = {}
    for name, cat_name, sku, size, cost, sell, reorder_qty, supp_name, batches in products_spec:
        category = cat_objs[cat_name]
        supplier = supplier_objs[supp_name]

        prod, _ = Product.objects.get_or_create(
            name=name,
            defaults={
                "category": category,
                "sku": sku,
                "size": size,
                "description": f"{name} ({size})",
                "created_by": admin_user,
            }
        )
        prod.category = category
        prod.sku = sku
        prod.size = size
        prod.save()

        # Stock Record
        stock, _ = Stock.objects.get_or_create(
            product=prod,
            defaults={
                "selling_price": sell,
                "low_stock_threshold": reorder_qty,
                "reorder_quantity": reorder_qty,
            }
        )
        stock.selling_price = sell
        stock.low_stock_threshold = reorder_qty
        stock.reorder_quantity = reorder_qty
        stock.save()

        # Batches
        for inv_num, q_rec, q_rem, c_price, days_ago, sn, em in batches:
            d_rec = today - timedelta(days=days_ago)
            batch, _ = StockBatch.objects.get_or_create(
                product=prod,
                supplier_invoice_number=inv_num,
                defaults={
                    "stock": stock,
                    "supplier_ref": supplier,
                    "supplier_name": supplier.name,
                    "date_received": d_rec,
                    "cost_price": c_price,
                    "quantity_received": q_rec,
                    "quantity_remaining": q_rem,
                    "is_active": (q_rem > 0),
                    "serial_number": sn,
                    "email": em,
                    "created_by": admin_user,
                }
            )
            batch.stock = stock
            batch.supplier_ref = supplier
            batch.supplier_name = supplier.name
            batch.date_received = d_rec
            batch.cost_price = c_price
            batch.quantity_received = q_rec
            batch.quantity_remaining = q_rem
            batch.is_active = (q_rem > 0)
            batch.serial_number = sn
            batch.email = em
            batch.save()

        stock.recalculate_quantity()
        product_objs[name] = prod
        print(f"  ✓ Product: {prod.name} | Available: {stock.quantity_available} | Price: ${stock.selling_price}")

    # -------------------------------------------------------------------------
    # 9. POS SALES & FIFO TRANSACTIONS
    # -------------------------------------------------------------------------
    print("\n[9/11] Seeding POS Sales & Historical Transactions...")

    sales_spec = [
        # (CustomerName, CashierUser, DaysAgo, PayMethod, Notes, ItemsList[(ProdName, Qty, SerialNumber)])
        ("Farai Mutandwa", cashier_user, 12, PaymentMethod.CASH, "Full cash payment in USD bills", [("Starlink Mini Kit", 1, "SLM-2026-90123")]),
        ("Kudzai Chisamba", cashier_user, 10, PaymentMethod.SWIPE, "Zimswitch / Visa POS terminal payment", [("iPhone 15 Pro Max 256GB", 1, "IMEI-354892109823412"), ("Baseus 100W 2M USB-C to USB-C Fast Charge Cable", 2, "")]),
        ("Sarah Van Wyk", admin_user, 9, PaymentMethod.ECOCASH, "EcoCash USD Merchant payment", [("Ruijie Reyee RG-EW3200GX PRO Wi-Fi 6 Router", 2, "")]),
        ("Tariro Zimuto", cashier_user, 8, PaymentMethod.BANK_TRANSFER, "Stanbic Bank Transfer", [("Apple MacBook Air M3 13\" 16GB/512GB", 1, "SN-C02GF892MD6M")]),
        ("Delta Mining Supplies (Pvt) Ltd", admin_user, 7, PaymentMethod.BANK_TRANSFER, "Direct Corporate PO payment", [("Starlink Standard Kit Gen 3", 2, ""), ("Cudy AX3000 Gigabit Wi-Fi 6 Router (WR3000)", 2, "")]),
        ("Apex Logistics Zimbabwe", manager_user, 6, PaymentMethod.BANK_TRANSFER, "Corporate fleet Wi-Fi expansion", [("Ruijie Reyee RG-RAP62620D Outdoor Access Point", 2, ""), ("Starlink Ethernet Adapter V2", 2, "")]),
        ("Tawanda Moyo", cashier_user, 5, PaymentMethod.INNBUCKS, "InnBucks barcode scanner checkout", [("Anker 737 Power Bank (PowerCore 24K 140W)", 1, ""), ("Anker Prime 67W 3-Port GaN Wall Charger", 1, "")]),
        ("Chipo Makoni", cashier_user, 4, PaymentMethod.CASH, "Over-the-counter cash sale", [("JBL Charge 5 Portable Waterproof Bluetooth Speaker", 1, "")]),
        ("Takudzwa Sithole", cashier_user, 3, PaymentMethod.SWIPE, "Mastercard POS tap", [("Sony WH-1000XM5 Wireless Noise Canceling Headphones", 1, "")]),
        ("Walk-in Customer", cashier_user, 2, PaymentMethod.CASH, "Walk-in cash accessories purchase", [("Baseus 100W 2M USB-C to USB-C Fast Charge Cable", 4, "")]),
        ("Walk-in Customer", cashier_user, 1, PaymentMethod.ECOCASH, "EcoCash walk-in payment", [("Anker Prime 67W 3-Port GaN Wall Charger", 2, "")]),
        ("Farai Mutandwa", cashier_user, 0, PaymentMethod.CASH, "Today's morning sale", [("Apple Watch Series 9 GPS 45mm", 1, ""), ("Baseus 100W 2M USB-C to USB-C Fast Charge Cable", 2, "")]),
    ]

    seeded_sales = []
    with transaction.atomic():
        for cust_name, user_obj, days_ago, pay_method, notes, items in sales_spec:
            customer = customer_objs[cust_name]
            sale_date = today - timedelta(days=days_ago)

            # Check if this sale was already seeded to avoid double deductions on repeat runs
            existing_sale = Sale.objects.filter(customer=customer, date_sold=sale_date, payment_method=pay_method).first()
            if existing_sale:
                seeded_sales.append(existing_sale)
                continue

            sale = Sale.objects.create(
                customer=customer,
                payment_method=pay_method,
                user=user_obj,
                notes=notes,
            )
            # Override date_sold
            Sale.objects.filter(pk=sale.pk).update(date_sold=sale_date)

            total_amount = Decimal("0.00")
            total_cost = Decimal("0.00")

            for prod_name, qty, sn in items:
                prod = product_objs[prod_name]
                unit_price = prod.stock.selling_price
                line_total = unit_price * Decimal(str(qty))

                # Identify FIFO batches
                if sn:
                    batches = list(prod.batches.filter(serial_number__iexact=sn, is_active=True, quantity_remaining__gt=0))
                    if not batches:
                        batches = list(prod.batches.filter(serial_number__iexact=sn))
                else:
                    batches = list(prod.batches.filter(serial_number="", is_active=True, quantity_remaining__gt=0).order_by("date_received", "id"))

                rem_qty = qty
                line_cost = Decimal("0.00")
                deductions = []

                for b in batches:
                    take = min(rem_qty, b.quantity_remaining) if b.quantity_remaining > 0 else 0
                    if take > 0:
                        b.quantity_remaining -= take
                        if b.quantity_remaining == 0:
                            b.is_active = False
                        b.save()
                    unit_c = b.cost_price or (unit_price * Decimal("0.75"))
                    line_cost += Decimal(str(take)) * unit_c
                    deductions.append((b, take, unit_c))
                    rem_qty -= take
                    if rem_qty <= 0:
                        break

                line_profit = line_total - line_cost
                total_amount += line_total
                total_cost += line_cost

                sale_item = SaleItem.objects.create(
                    sale=sale,
                    product=prod,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=line_total,
                    cost_price=line_cost,
                    profit=line_profit,
                    serial_number=sn,
                )

                for b, take, unit_c in deductions:
                    SaleBatchDeduction.objects.create(
                        sale_item=sale_item,
                        batch=b,
                        quantity_deducted=take,
                        unit_cost=unit_c
                    )

                prod.stock.recalculate_quantity()

            sale.total_amount = total_amount
            sale.total_cost = total_cost
            sale.total_profit = total_amount - total_cost
            sale.save()
            seeded_sales.append(sale)
            print(f"  ✓ Sale {sale.invoice_number}: {sale.customer.name} | Total: ${sale.total_amount} ({sale.payment_method})")

    # -------------------------------------------------------------------------
    # 10. EXPENSE CATEGORIES & EXPENSES
    # -------------------------------------------------------------------------
    print("\n[10/11] Seeding Expense Categories & Operational Expenses...")

    expense_cats = [
        ("Store Rent & Premises", "Monthly lease for Celestial Mall retail location", Decimal("850.00"), True, "MONTHLY"),
        ("Solar & Grid Electricity", "ZETDC prepaid tokens & solar system inverter servicing", Decimal("180.00"), True, "MONTHLY"),
        ("Fiber Internet & Communications", "Liquid Intelligent Technologies high-speed store link", Decimal("120.00"), True, "MONTHLY"),
        ("Packaging, Bags & Receipt Rolls", "Branded carrier bags and 80mm thermal receipt roll boxes", Decimal("75.00"), True, "MONTHLY"),
        ("Staff Refreshments & Logistics", "Tea, drinking water dispensers and local stock transport", Decimal("60.00"), True, "WEEKLY"),
        ("Marketing & Social Ads", "Facebook, Instagram & Google Ads store promotions", Decimal("150.00"), True, "MONTHLY"),
        ("Hardware Maintenance & Security", "Mall security levy and hardware tools", Decimal("100.00"), True, "MONTHLY"),
    ]

    exp_cat_objs = {}
    for name, desc, def_amt, is_rec, rec_int in expense_cats:
        ec, _ = ExpenseCategory.objects.get_or_create(
            name=name,
            defaults={
                "description": desc,
                "default_amount": def_amt,
                "is_recurring": is_rec,
                "recurring_interval": rec_int,
            }
        )
        ec.description = desc
        ec.default_amount = def_amt
        ec.is_recurring = is_rec
        ec.recurring_interval = rec_int
        ec.save()
        exp_cat_objs[name] = ec

    expenses_spec = [
        ("Celestial Mall Monthly Shop Lease", "Store Rent & Premises", Decimal("850.00"), 14, "Bank Transfer", "RCP-MALL-2026-09", manager_user),
        ("ZETDC 500kWh Prepaid Electricity Tokens", "Solar & Grid Electricity", Decimal("180.00"), 12, "EcoCash", "ZETDC-99210982", admin_user),
        ("Liquid Telecom Dedicated Fiber Monthly Bill", "Fiber Internet & Communications", Decimal("120.00"), 10, "Swipe", "LQD-INV-4412", manager_user),
        ("Box of 50 Rolls 80mm Thermal Till Rolls", "Packaging, Bags & Receipt Rolls", Decimal("45.00"), 8, "Cash", "STAT-0912", cashier_user),
        ("500 Branded Heavy Duty Shopping Bags", "Packaging, Bags & Receipt Rolls", Decimal("75.00"), 6, "Cash", "BAGS-552", cashier_user),
        ("Mineral Water Dispensers Refill (5 Bottles)", "Staff Refreshments & Logistics", Decimal("30.00"), 5, "Cash", "WTR-110", cashier_user),
        ("Google Ads Campaign - Starlink Zimbabwe Promo", "Marketing & Social Ads", Decimal("100.00"), 4, "Swipe", "GGL-ADS-881", admin_user),
        ("Mall Security & Service Charge Levy", "Hardware Maintenance & Security", Decimal("65.00"), 2, "Bank Transfer", "SEC-MALL-01", manager_user),
        ("Staff Friday Refreshments", "Staff Refreshments & Logistics", Decimal("25.00"), 1, "Cash", "REF-0915", cashier_user),
    ]

    for title, cat_name, amt, days_ago, pay_m, ref, recorded_by in expenses_spec:
        cat = exp_cat_objs[cat_name]
        exp_date = today - timedelta(days=days_ago)
        exp, _ = Expense.objects.get_or_create(
            title=title,
            date=exp_date,
            defaults={
                "category": cat,
                "amount": amt,
                "payment_method": pay_m,
                "reference_number": ref,
                "recorded_by": recorded_by,
                "notes": f"Recorded for {cat_name}"
            }
        )
        exp.category = cat
        exp.amount = amt
        exp.payment_method = pay_m
        exp.reference_number = ref
        exp.recorded_by = recorded_by
        exp.save()
        print(f"  ✓ Expense: {exp.title} (${exp.amount} via {exp.payment_method})")

    # -------------------------------------------------------------------------
    # 11. NOTIFICATIONS & FISCAL RECEIPTS
    # -------------------------------------------------------------------------
    print("\n[11/11] Seeding System Notifications & Fiscal Records...")

    # Low Stock Notifications
    p_adapter = product_objs["Starlink Ethernet Adapter V2"]
    Notification.objects.get_or_create(
        title="Low Stock Alert: Starlink Ethernet Adapter V2",
        defaults={
            "message": f"Inventory for '{p_adapter.name}' has dropped to {p_adapter.available_quantity} unit(s), which is at or below the reorder threshold of {p_adapter.stock.reorder_quantity}.",
            "notification_type": Notification.NotificationType.LOW_STOCK,
            "product": p_adapter,
            "severity": "WARNING",
            "is_read": False,
            "link_url": f"/inventory/?q=Ethernet",
        }
    )

    p_apple_20w = product_objs["Apple 20W USB-C Power Adapter"]
    Notification.objects.get_or_create(
        title="Stock Depleted: Apple 20W USB-C Power Adapter",
        defaults={
            "message": f"Inventory for '{p_apple_20w.name}' is completely depleted (0 units remaining). Please contact Apple Authorized Distributor for a restock batch.",
            "notification_type": Notification.NotificationType.LOW_STOCK,
            "product": p_apple_20w,
            "severity": "CRITICAL",
            "is_read": False,
            "link_url": f"/inventory/?q=Apple+20W",
        }
    )

    Notification.objects.get_or_create(
        title="Welcome to 21 Void Technologies Gadget Store",
        defaults={
            "message": "System environment initialized successfully. Multi-environment database architecture (SQLite & PostgreSQL) and thermal POS printing are fully operational.",
            "notification_type": Notification.NotificationType.SYSTEM,
            "severity": "INFO",
            "is_read": True,
            "link_url": "/dashboard/",
        }
    )
    print("  ✓ Notifications created")

    # Sample Fiscal Receipts for recent sales
    for idx, sale in enumerate(seeded_sales[:4]):
        FiscalReceipt.objects.get_or_create(
            local_receipt_number=sale.id,
            defaults={
                "doc_type": FiscalReceipt.TYPE_INVOICE,
                "inv_number": 1000 + sale.id,
                "inv_number_global": 5000 + sale.id,
                "doc_currency": "USD",
                "my_yyy_mm_dd_date": sale.date_sold,
                "my_24hr_time_format_with_seconds": "14:35:20",
                "document_total": sale.total_amount,
                "tax_15_perc_sales_total": sale.total_amount,
                "tax_amt_15_perc": round(sale.total_amount * Decimal("0.15") / Decimal("1.15"), 2),
                "machinecode": "MACH-01",
                "the_password": "pass",
                "buyer_register_name": sale.customer.name,
                "phone_no": sale.customer.phone,
                "email": sale.customer.email,
                "qr_code_url": f"https://fdmstest.zimra.co.zw/verify?dev=TEST-DEV-01&rcpt={1000 + sale.id}",
                "status": FiscalReceipt.STATUS_SYNCED,
                "synced_at": timezone.now(),
            }
        )
    print("  ✓ Sample Fiscal Receipts synchronized")

    print("\n============================================================")
    print("  SEEDING COMPLETE SUMMARY:")
    print(f"  - Users: {User.objects.count()} (root@gmail.com / toor ready)")
    print(f"  - Categories: {Category.objects.count()}")
    print(f"  - Suppliers: {Supplier.objects.count()}")
    print(f"  - Products: {Product.objects.count()}")
    print(f"  - Stocks: {Stock.objects.count()}")
    print(f"  - StockBatches: {StockBatch.objects.count()}")
    print(f"  - Customers: {Customer.objects.count()}")
    print(f"  - Sales: {Sale.objects.count()}")
    print(f"  - SaleItems: {SaleItem.objects.count()}")
    print(f"  - SaleBatchDeductions: {SaleBatchDeduction.objects.count()}")
    print(f"  - Expense Categories: {ExpenseCategory.objects.count()}")
    print(f"  - Expenses: {Expense.objects.count()}")
    print(f"  - Printers: {Printer.objects.count()}")
    print(f"  - Notifications: {Notification.objects.count()}")
    print(f"  - Fiscal Receipts: {FiscalReceipt.objects.count()}")
    print("============================================================\n")


if __name__ == "__main__":
    run_seed()
