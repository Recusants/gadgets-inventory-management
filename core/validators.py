"""
Core input validators for 21 Void Technologies.
Every entity has its own dedicated validator function returning a dictionary of field errors:
    errors = {
        'field_name': 'Descriptive error message',
        ...
    }
Strict constraint: Zero Django Forms. No Form or ModelForm imports anywhere.
"""

import re
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.utils.dateparse import parse_date

# Email regular expression pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def _parse_decimal(value, default=None):
    """Safely parse decimal number or return default."""
    if value is None:
        return default
    cleaned = str(value).strip().replace('$', '').replace(',', '')
    if not cleaned:
        return default
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return default

def _parse_custom_date(value, default=None):
    """Support YYYY-MM-DD or DD/MM/YYYY date strings."""
    if not value or not str(value).strip():
        return default
    val_str = str(value).strip()
    # Try YYYY-MM-DD
    parsed = parse_date(val_str)
    if parsed:
        return parsed
    # Try DD/MM/YYYY
    try:
        dt = datetime.strptime(val_str, '%d/%m/%Y')
        return dt.date()
    except ValueError:
        pass
    # Try DD-MM-YYYY
    try:
        dt = datetime.strptime(val_str, '%d-%m-%Y')
        return dt.date()
    except ValueError:
        pass
    return default


def validate_login(data):
    """Validate login inputs."""
    errors = {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username:
        errors['username'] = 'Username is required.'
    if not password:
        errors['password'] = 'Password is required.'

    return errors


def validate_user(data, instance=None):
    """Validate User creation and update."""
    from accounts.models import User, UserRole
    errors = {}

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    email = data.get('email', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    role = data.get('role', '').strip()
    phone = data.get('phone', '').strip()

    # Username validation
    if not instance:
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username) > 150:
            errors['username'] = 'Username must be 150 characters or fewer.'
        elif not re.match(r'^[\w.@+-]+$', username):
            errors['username'] = 'Username contains invalid characters.'
        elif User.objects.filter(username__iexact=username).exists():
            errors['username'] = f'A user with username "{username}" already exists.'

    # Password validation
    if not instance:
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters long.'
    else:
        if password and len(password) < 6:
            errors['password'] = 'New password must be at least 6 characters long.'

    # Email
    if email:
        if not EMAIL_REGEX.match(email):
            errors['email'] = 'Enter a valid email address.'
        elif len(email) > 254:
            errors['email'] = 'Email address is too long.'

    # Role
    if role and role not in UserRole.values:
        errors['role'] = f'Role must be one of: {", ".join(UserRole.values)}'

    return errors



def validate_category(data, instance=None):
    """Validate Category data."""
    from inventory.models import Category
    errors = {}
    name = data.get('name', '').strip()

    if not name:
        errors['name'] = 'Category name is required.'
    elif len(name) > 100:
        errors['name'] = 'Category name must be 100 characters or fewer.'
    else:
        qs = Category.objects.filter(name__iexact=name)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            errors['name'] = f'A category named "{name}" already exists.'

    return errors


def validate_product(data, instance=None):
    """
    Validate Product master definition.
    Serial numbers are optional at checkout and NOT required on product creation.
    """
    from inventory.models import Category
    errors = {}
    
    name = data.get('name', '').strip()
    category_id = data.get('category_id') or data.get('category')
    selling_price_raw = data.get('selling_price') or data.get('amount_sold')

    # Product Name
    if not name:
        errors['name'] = 'Product name is required.'
    elif len(name) > 200:
        errors['name'] = 'Product name must be 200 characters or fewer.'

    # Category
    if not category_id:
        errors['category'] = 'Please select a category.'
    else:
        try:
            if not Category.objects.filter(pk=category_id).exists():
                errors['category'] = 'Selected category does not exist.'
        except (ValueError, TypeError):
            errors['category'] = 'Invalid category selected.'

    # Optional initial selling price
    if selling_price_raw is not None and str(selling_price_raw).strip() != '':
        sp = _parse_decimal(selling_price_raw)
        if sp is None or sp < Decimal('0.00'):
            errors['selling_price'] = 'Selling price must be a valid positive number.'

    return errors


def validate_receive_invoice(data):
    """Validate incoming Supplier Invoice / Stock Intake."""
    from inventory.models import Product
    errors = {}

    product_id = data.get('product_id') or data.get('product')
    qty_raw = data.get('quantity') or data.get('quantity_received')
    cost_price_raw = data.get('cost_price') or data.get('amount_bought')
    selling_price_raw = data.get('selling_price') or data.get('amount_sold')

    if not product_id:
        errors['product'] = 'Please select a product.'
    else:
        try:
            if not Product.objects.filter(pk=product_id).exists():
                errors['product'] = 'Selected product does not exist.'
        except (ValueError, TypeError):
            errors['product'] = 'Invalid product selected.'

    # Quantity
    try:
        qty = int(qty_raw)
        if qty < 1:
            errors['quantity'] = 'Quantity received must be at least 1.'
    except (ValueError, TypeError):
        errors['quantity'] = 'Quantity must be a valid whole number.'

    # Cost price
    cost = _parse_decimal(cost_price_raw)
    if cost is None or cost < Decimal('0.00'):
        errors['cost_price'] = 'Valid unit cost price is required.'

    # Selling price
    if selling_price_raw is not None and str(selling_price_raw).strip() != '':
        sp = _parse_decimal(selling_price_raw)
        if sp is None or sp < Decimal('0.00'):
            errors['selling_price'] = 'Selling price must be a valid positive number.'

    return errors


def validate_supplier(data, instance=None):
    """Validate Supplier data."""
    from inventory.models import Supplier
    errors = {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()

    if not name:
        errors['name'] = 'Supplier name is required.'
    elif len(name) > 150:
        errors['name'] = 'Supplier name must be 150 characters or fewer.'
    else:
        qs = Supplier.objects.filter(name__iexact=name)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            errors['name'] = f'A supplier named "{name}" already exists.'

    if email and not EMAIL_REGEX.match(email):
        errors['email'] = 'Enter a valid email address.'

    return errors


def validate_customer(data, instance=None):
    """Validate Customer data."""
    errors = {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()

    if not name:
        errors['name'] = 'Customer name is required.'
    elif len(name) > 150:
        errors['name'] = 'Customer name must be 150 characters or fewer.'

    if not phone:
        errors['phone'] = 'Customer phone number is required.'
    elif len(phone) < 5 or len(phone) > 30:
        errors['phone'] = 'Phone number must be between 5 and 30 characters.'

    if email:
        if not EMAIL_REGEX.match(email):
            errors['email'] = 'Enter a valid email address.'
        elif len(email) > 254:
            errors['email'] = 'Email address is too long.'

    return errors


def validate_sale(data, instance=None):
    """
    Validate Sale / Checkout transaction.
    Supports cart items array: [{product_id, quantity, unit_price, serial_number}].
    Enforces rule: Serial number only acceptable when quantity is 1!
    """
    from inventory.models import Product
    from sales.models import Customer, PaymentMethod
    errors = {}

    customer_id = data.get('customer_id') or data.get('customer')
    payment_method = data.get('payment_method', '').strip()

    # Customer is optional (defaults automatically to Walk-in Customer if blank)
    if customer_id:
        try:
            if not Customer.objects.filter(pk=customer_id).exists():
                errors['customer'] = 'Selected customer does not exist.'
        except (ValueError, TypeError):
            errors['customer'] = 'Invalid customer ID.'

    # Payment Method
    if not payment_method:
        errors['payment_method'] = 'Please select a payment method.'
    elif payment_method not in PaymentMethod.values:
        errors['payment_method'] = f'Payment method must be one of: {", ".join(PaymentMethod.values)}'

    # Check cart items
    cart_raw = data.get('cart_items')
    cart_items = []
    if cart_raw:
        if isinstance(cart_raw, str):
            try:
                cart_items = json.loads(cart_raw)
            except Exception:
                errors['cart'] = 'Invalid cart data format.'
        elif isinstance(cart_raw, list):
            cart_items = cart_raw

    # Fallback to single item if cart_items not provided
    if not cart_items:
        prod_id = data.get('product') or data.get('product_id')
        amount_raw = data.get('amount_sold')
        qty_raw = data.get('quantity', 1)
        sn_raw = data.get('serial_number', '').strip()
        if prod_id:
            cart_items = [{
                'product_id': prod_id,
                'quantity': qty_raw,
                'unit_price': amount_raw,
                'serial_number': sn_raw
            }]

    if not cart_items:
        errors['cart'] = 'Cart is empty. Please add at least one item.'
    else:
        for idx, item in enumerate(cart_items):
            pid = item.get('product_id')
            qty = item.get('quantity')
            price = item.get('unit_price')
            sn = str(item.get('serial_number') or '').strip()

            if not pid:
                errors[f'item_{idx}_product'] = 'Product ID missing.'
                continue

            prod = Product.objects.filter(pk=pid).first()
            if not prod:
                errors[f'item_{idx}_product'] = 'Selected product does not exist.'
                continue

            try:
                q = int(qty)
                if q < 1:
                    errors[f'item_{idx}_qty'] = f'Quantity for {prod.name} must be at least 1.'
                elif prod.available_quantity < q:
                    errors[f'item_{idx}_qty'] = f'Insufficient stock for "{prod.name}". Available: {prod.available_quantity}, requested: {q}.'
            except (ValueError, TypeError):
                errors[f'item_{idx}_qty'] = f'Invalid quantity for {prod.name}.'

            p_dec = _parse_decimal(price)
            if p_dec is None or p_dec < Decimal('0.00'):
                errors[f'item_{idx}_price'] = f'Invalid selling price for {prod.name}.'

            # Strict rule: serial number only acceptable when quantity is 1!
            if sn and int(qty or 0) > 1:
                errors[f'item_{idx}_sn'] = f'Serial number for "{prod.name}" can only be recorded when quantity is 1. Please add each serialized item as its own line.'

    return errors


def validate_settings(data):
    """Validate Company Settings."""
    errors = {}
    name = data.get('company_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()

    if not name:
        errors['company_name'] = 'Company name is required.'
    elif len(name) > 150:
        errors['company_name'] = 'Company name must be 150 characters or fewer.'

    if phone and len(phone) > 30:
        errors['phone'] = 'Phone number must be 30 characters or fewer.'

    if email:
        if not EMAIL_REGEX.match(email):
            errors['email'] = 'Enter a valid company email address.'
        elif len(email) > 254:
            errors['email'] = 'Email address is too long.'

    return errors


validate_company_settings = validate_settings

