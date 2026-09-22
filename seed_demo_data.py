"""
Seed demonstration data matching the exact 21 Void Technologies UI mockup.
"""

import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from accounts.models import User, UserRole
from inventory.models import Category, Product, ProductStatus
from sales.models import Customer, Sale, PaymentMethod
from core.models import CompanySetting

print("Seeding demo data...")

# 1. Company Settings
comp = CompanySetting.get_settings()
comp.company_name = "21 Void Technologies"
comp.tagline = "Fusing Technology With Market Intelligence"
comp.phone = "+263 77 123 4567"
comp.email = "info@21void.com"
comp.address = "Harare, Zimbabwe"
comp.currency_symbol = "$"
comp.currency_code = "USD"
comp.receipt_header_note = "Official Purchase Receipt"
comp.receipt_footer_note = "Thank you for doing business with 21 Void Technologies! All products guaranteed authentic."
comp.save()

# 2. Administrator matching Mockup Topbar (James Zvokureva / Admin)
admin_user, _ = User.objects.get_or_create(
    username="admin",
    defaults={
        "first_name": "James",
        "last_name": "Zvokureva",
        "email": "admin@21void.com",
        "role": UserRole.ADMIN,
        "is_staff": True,
        "is_superuser": True
    }
)
admin_user.set_password("Admin@21Void2026")
admin_user.first_name = "James"
admin_user.last_name = "Zvokureva"
admin_user.role = UserRole.ADMIN
admin_user.save()

# 3. Categories
cat_internet, _ = Category.objects.get_or_create(
    name="Internet Equipment",
    defaults={"description": "Satellite kits, wireless routers, access points and switches"}
)
cat_power, _ = Category.objects.get_or_create(
    name="Power Solutions",
    defaults={"description": "Solar inverters, backup batteries and power supplies"}
)

# 4. Customers
customers_data = [
    ("John Doe", "0771234567", "john.doe@example.com"),
    ("Mary Chikati", "0772345678", "mary.chikati@example.com"),
    ("Tendai Moyo", "0773456789", "tendai.moyo@example.com"),
    ("Blessing Ndlovu", "0774567890", "blessing.n@example.com"),
    ("Gift Chitiyo", "0775678901", "gift.c@example.com"),
]
customer_objs = {}
for name, phone, email in customers_data:
    cust, _ = Customer.objects.get_or_create(
        phone=phone,
        defaults={"name": name, "email": email, "created_by": admin_user}
    )
    cust.name = name
    cust.email = email
    cust.save()
    customer_objs[name] = cust

# 5. Products & Sales matching mockup
mockup_items = [
    # (Name, Serial, Account, Cost, Sell, DateRec, SoldDate, CustName, IsSold, Status)
    ("Starlink Mini", "SN123456789", "ACC-458921", Decimal("280.00"), Decimal("350.00"), date(2026, 9, 16), date(2026, 9, 20), "John Doe", True, ProductStatus.SOLD),
    ("Ruijie Router", "SN987654321", "ACC-741258", Decimal("160.00"), Decimal("180.00"), date(2026, 9, 14), date(2026, 9, 19), "Mary Chikati", True, ProductStatus.SOLD),
    ("Starlink Standard", "SN112233445", "ACC-664987", Decimal("280.00"), Decimal("420.00"), date(2026, 9, 10), date(2026, 9, 18), "Tendai Moyo", True, ProductStatus.SOLD),
    ("Cudy AP", "SN778899112", "ACC-223344", Decimal("110.00"), Decimal("150.00"), date(2026, 9, 12), date(2026, 9, 17), "Blessing Ndlovu", True, ProductStatus.SOLD),
    ("Starlink Mini", "SN554433221", "ACC-998877", Decimal("280.00"), Decimal("350.00"), date(2026, 9, 10), date(2026, 9, 16), "Gift Chitiyo", True, ProductStatus.SOLD),
    
    # In-Stock Products
    ("Cudy AX3000", "SN456789123", "ACC-369852", Decimal("110.00"), Decimal("150.00"), date(2026, 9, 12), None, None, False, ProductStatus.IN_STOCK),
    ("Ruijie Gateway EG105G-V3", "SN556677889", "ACC-963741", Decimal("120.00"), Decimal("160.00"), date(2026, 9, 8), None, None, False, ProductStatus.IN_STOCK),
    ("Cudy AC1200", "SN778899001", "ACC-739521", Decimal("70.00"), Decimal("100.00"), date(2026, 9, 5), None, None, False, ProductStatus.IN_STOCK),
    ("Starlink Mini", "SN9988776655", "ACC-147258", Decimal("280.00"), Decimal("350.00"), date(2026, 9, 1), None, None, False, ProductStatus.IN_STOCK),
    ("Ruijie RAP62620D", "SN334455667", "ACC-556677", Decimal("160.00"), Decimal("210.00"), date(2026, 9, 4), None, None, False, ProductStatus.IN_STOCK),
    ("MikroTik hEX S", "SN889900112", "ACC-112233", Decimal("65.00"), Decimal("95.00"), date(2026, 9, 3), None, None, False, ProductStatus.IN_STOCK),
    ("Starlink High Performance", "SN445566778", "ACC-778899", Decimal("550.00"), Decimal("750.00"), date(2026, 9, 2), None, None, False, ProductStatus.IN_STOCK),
]

for name, sn, acc, cost, sell, d_rec, d_sold, c_name, is_sold, status in mockup_items:
    prod, _ = Product.objects.get_or_create(
        serial_number=sn,
        defaults={
            "name": name,
            "account_number": acc,
            "category": cat_internet,
            "cost_price": cost,
            "selling_price": sell,
            "received_date": d_rec,
            "status": status,
            "created_by": admin_user
        }
    )
    prod.name = name
    prod.account_number = acc
    prod.cost_price = cost
    prod.selling_price = sell
    prod.received_date = d_rec
    prod.status = status
    prod.save()

    if is_sold and c_name and c_name in customer_objs:
        cust = customer_objs[c_name]
        if not hasattr(prod, 'sale') or prod.sale is None:
            Sale.objects.create(
                product=prod,
                customer=cust,
                amount_sold=sell,
                date_sold=d_sold or date.today(),
                payment_method=PaymentMethod.CASH,
                user=admin_user
            )

print(f"Demo data successfully populated! Products: {Product.objects.count()}, Sales: {Sale.objects.count()}, Customers: {Customer.objects.count()}")
