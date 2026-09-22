"""
Function-Based Views for Sales, POS Multi-Item Checkout, Customers, and PDF Receipts.
Strictly zero Django Forms, 100% FBVs, uniform JSON envelope responses, FIFO batch deduction.
"""

from decimal import Decimal
import io
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import Customer, Sale, SaleItem, SaleBatchDeduction, PaymentMethod
from inventory.models import Product, Stock, StockBatch, Category
from core.models import CompanySetting
from core.validators import validate_customer, validate_sale, _parse_decimal, _parse_custom_date
from core.responses import success_response, error_response, permission_denied_response
from core.decorators import admin_required, manager_or_admin_required, ajax_required


# ==============================================================================
# SALES & TRANSACTIONS
# ==============================================================================

def sale_list_view(request):
    """Render full page shell for Sales with initial table pre-rendered."""
    categories = Category.objects.all().order_by('name')
    queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items__product').all().order_by('-created_at')
    paginator = Paginator(queryset, 10)
    sales = paginator.page(1)
    return render(request, 'sales/sale_list.html', {
        'categories': categories,
        'sales': sales,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def sale_table_partial(request):
    """
    Returns table body and pagination partial for Sales.
    Matches columns: Date | Invoice | Items | Customer | Amount Sold | Profit | Payment | Actions
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    from_date_raw = request.GET.get('from_date', '').strip()
    to_date_raw = request.GET.get('to_date', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items__product__category').all().order_by('-created_at')

    if query:
        queryset = queryset.filter(
            Q(invoice_number__icontains=query) |
            Q(items__product__name__icontains=query) |
            Q(items__serial_number__icontains=query) |
            Q(customer__name__icontains=query) |
            Q(customer__phone__icontains=query)
        ).distinct()

    if category_id:
        queryset = queryset.filter(items__product__category_id=category_id).distinct()

    if from_date_raw:
        from_date = _parse_custom_date(from_date_raw)
        if from_date:
            queryset = queryset.filter(date_sold__gte=from_date)

    if to_date_raw:
        to_date = _parse_custom_date(to_date_raw)
        if to_date:
            queryset = queryset.filter(date_sold__lte=to_date)

    paginator = Paginator(queryset, 10)
    try:
        sales = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        sales = paginator.page(1)

    return render(request, 'sales/partials/sale_table.html', {
        'sales': sales,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def sale_add_modal(request):
    """Return Record Sale modal HTML partial."""
    in_stock_products = Product.objects.filter(stock__quantity_available__gt=0).order_by('name')
    customers = Customer.objects.all().order_by('name')
    payment_methods = PaymentMethod.choices
    return render(request, 'sales/partials/sale_add_modal.html', {
        'products': in_stock_products,
        'customers': customers,
        'payment_methods': payment_methods,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })


def sale_detail_modal(request, pk):
    """Return Sale Detail & Receipt Preview modal HTML partial."""
    sale = get_object_or_404(Sale.objects.select_related('customer', 'user').prefetch_related('items__product'), pk=pk)
    company_settings = CompanySetting.get_settings()
    return render(request, 'sales/partials/sale_detail_modal.html', {
        'sale': sale,
        'settings': company_settings,
    })


@require_POST
def sale_create(request):
    """
    Records a completed sale with FIFO deduction across batches.
    Supports multi-item cart JSON payload or single item fallback.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    errors = validate_sale(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Sale Validation Failed",
                message="Please resolve the errors highlighted below.",
                errors=errors
            )
        return redirect('sales:checkout')

    cust_id = request.POST.get('customer') or request.POST.get('customer_id')
    if cust_id:
        customer = Customer.objects.get(pk=cust_id)
    else:
        customer = Customer.get_default_customer()
    payment_method = request.POST.get('payment_method') or PaymentMethod.CASH
    notes = request.POST.get('notes', '').strip()

    # Parse cart items
    cart_raw = request.POST.get('cart_items')
    cart_items = []
    if cart_raw:
        try:
            cart_items = json.loads(cart_raw) if isinstance(cart_raw, str) else cart_raw
        except Exception:
            cart_items = []

    if not cart_items:
        prod_id = request.POST.get('product') or request.POST.get('product_id')
        qty = int(request.POST.get('quantity', 1))
        unit_price = _parse_decimal(request.POST.get('amount_sold'))
        sn = request.POST.get('serial_number', '').strip()
        cart_items = [{
            'product_id': prod_id,
            'quantity': qty,
            'unit_price': float(unit_price) if unit_price else 0.0,
            'serial_number': sn
        }]

    sale_user = request.user if request.user.is_authenticated else None
    if not sale_user:
        from django.contrib.auth import get_user_model
        sale_user = get_user_model().objects.filter(is_active=True).first()

    with transaction.atomic():
        sale = Sale.objects.create(
            customer=customer,
            payment_method=payment_method,
            user=sale_user,
            notes=notes
        )

        total_amount = Decimal('0.00')
        total_cost = Decimal('0.00')

        for item in cart_items:
            prod = Product.objects.select_for_update().get(pk=item['product_id'])
            qty = int(item['quantity'])
            unit_price = Decimal(str(item['unit_price']))
            sn = str(item.get('serial_number') or '').strip()
            line_total = unit_price * qty

            # FIFO Deduction from active batches ordered by date_received ASC, id ASC
            batches = prod.batches.filter(is_active=True, quantity_remaining__gt=0).order_by('date_received', 'id')
            rem_qty = qty
            line_cost = Decimal('0.00')
            deductions = []

            for b in batches:
                take = min(rem_qty, b.quantity_remaining)
                b.quantity_remaining -= take
                if b.quantity_remaining == 0:
                    b.is_active = False
                b.save()

                line_cost += Decimal(str(take)) * b.cost_price
                deductions.append((b, take, b.cost_price))
                rem_qty -= take
                if rem_qty == 0:
                    break

            line_profit = line_total - line_cost

            sale_item = SaleItem.objects.create(
                sale=sale,
                product=prod,
                quantity=qty,
                unit_price=unit_price,
                total_price=line_total,
                cost_price=line_cost,
                profit=line_profit,
                serial_number=sn
            )

            for b, take_qty, cost_unit in deductions:
                SaleBatchDeduction.objects.create(
                    sale_item=sale_item,
                    batch=b,
                    quantity_deducted=take_qty,
                    unit_cost=cost_unit
                )

            # Update Stock quantity
            if hasattr(prod, 'stock') and prod.stock:
                prod.stock.recalculate_quantity()

            total_amount += line_total
            total_cost += line_cost

        sale.total_amount = total_amount
        sale.total_cost = total_cost
        sale.total_profit = total_amount - total_cost
        sale.save()

    if is_ajax:
        return success_response(
            title="Sale Completed",
            message=f'Sale recorded successfully! Invoice: {sale.invoice_number}',
            data={
                "sale_id": sale.pk,
                "invoice_number": sale.invoice_number,
                "receipt_url": f"/sales/{sale.pk}/receipt/"
            }
        )
    return redirect('sales:sale_list')


@require_POST
def sale_delete(request, pk):
    """
    Voids/Deletes a sale. Restricted to Admins.
    """
    if request.user.is_authenticated and not (request.user.is_admin_role() or request.user.is_manager_role()):
        return permission_denied_response(
            title="Access Denied",
            message="Only Administrators or Managers can void sales transactions."
        )

    sale = get_object_or_404(Sale, pk=pk)
    inv = sale.invoice_number
    sale.delete()

    return success_response(
        title="Sale Voided",
        message=f'Sale {inv} has been voided.'
    )


# ==============================================================================
# POS CHECKOUT SCREEN & AJAX SELECTORS
# ==============================================================================

def pos_checkout_view(request):
    """Render high-speed dedicated POS checkout screen with cart & FIFO."""
    categories = Category.objects.all().order_by('name')
    # Limit initial matches to 10 for rapid load
    initial_products = Product.objects.filter(stock__quantity_available__gt=0).select_related('stock', 'category')[:10]
    default_customer = Customer.get_default_customer()
    other_customers = list(Customer.objects.exclude(id=default_customer.id).order_by('name')[:9])
    initial_customers = [default_customer] + other_customers
    payment_methods = PaymentMethod.choices
    company_settings = CompanySetting.get_settings()

    return render(request, 'sales/checkout.html', {
        'products': initial_products,
        'categories': categories,
        'customers': initial_customers,
        'default_customer': default_customer,
        'payment_methods': payment_methods,
        'settings': company_settings,
    })


def customer_search_ajax(request):
    """Return limited matching customers (max 10) for POS customer selector."""
    query = request.GET.get('q', '').strip()
    qs = Customer.objects.all().order_by('name')
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
    results = []
    for c in qs[:10]:
        results.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'email': c.email
        })
    return JsonResponse({'status': 'success', 'results': results})


# ==============================================================================
# PDF RECEIPT GENERATION (Offline ReportLab Engine)
# ==============================================================================

def receipt_pdf_view(request, pk):
    """
    Generate professional offline PDF receipt for a sale.
    Uses ReportLab to create branded receipt with multi-item table and optional serials.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    sale = get_object_or_404(Sale.objects.select_related('customer', 'user').prefetch_related('items__product'), pk=pk)
    settings_obj = CompanySetting.get_settings()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b')
    )
    item_title = ParagraphStyle(
        'ItemTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )
    item_sn = ParagraphStyle(
        'ItemSN',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2563eb')
    )
    cell_text = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    bold_cell = ParagraphStyle(
        'BoldCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    # 1. Header (Company Info, Logo & Document Title)
    import os
    from django.conf import settings
    from reportlab.platypus import Image as RLImage

    logo_path = None
    if settings_obj.logo:
        try:
            if os.path.exists(settings_obj.logo.path):
                logo_path = settings_obj.logo.path
        except Exception:
            pass

    if not logo_path:
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.jpg')

    if logo_path and os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=48, height=48, mask='auto')

        header_data = [
            [
                logo_img,
                Paragraph(f"<b>{settings_obj.company_name.upper()}</b><br/><font size='8' color='#64748b'>{settings_obj.tagline}<br/>{settings_obj.address}<br/>Phone: {settings_obj.phone} | Email: {settings_obj.email}</font>", subtitle_style),
                Paragraph(f"<font color='#2563eb' size='13'><b>OFFICIAL SALES RECEIPT</b></font><br/><b>Invoice #:</b> {sale.invoice_number}<br/><b>Date:</b> {sale.date_sold.strftime('%d %b %Y')}<br/><b>Payment:</b> {sale.payment_method}", ParagraphStyle('RightMeta', parent=subtitle_style, alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[55, 275, 202])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
    else:
        header_data = [
            [
                Paragraph(f"<b>{settings_obj.company_name.upper()}</b>", title_style),
                Paragraph("<b>OFFICIAL SALES RECEIPT</b>", ParagraphStyle('RightTitle', parent=title_style, alignment=2, textColor=colors.HexColor('#2563eb'), fontSize=16))
            ],
            [
                Paragraph(f"{settings_obj.tagline}<br/>{settings_obj.address}<br/>Phone: {settings_obj.phone} | Email: {settings_obj.email}", subtitle_style),
                Paragraph(f"<b>Invoice #:</b> {sale.invoice_number}<br/><b>Date:</b> {sale.date_sold.strftime('%d %b %Y')}<br/><b>Payment:</b> {sale.payment_method}", ParagraphStyle('RightMeta', parent=subtitle_style, alignment=2))
            ]
        ]
        header_table = Table(header_data, colWidths=[320, 212])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Divider
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceBefore=5, spaceAfter=15))

    # 2. Customer & Cashier Meta
    cashier_name = sale.user.get_full_name() or sale.user.username if sale.user else "Staff"
    cust_data = [
        [
            Paragraph(f"<b>CUSTOMER DETAILS:</b><br/>Name: <b>{sale.customer.name}</b><br/>Phone: {sale.customer.phone}" + (f"<br/>Email: {sale.customer.email}" if sale.customer.email else ""), cell_text),
            Paragraph(f"<b>TRANSACTION DETAILS:</b><br/>Processed By: <b>{cashier_name}</b><br/>Items Sold: {sale.item_count} units", cell_text)
        ]
    ]
    cust_table = Table(cust_data, colWidths=[270, 262])
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(cust_table)
    elements.append(Spacer(1, 15))

    # 3. Itemized Table
    item_rows = [
        [
            Paragraph("<b>#</b>", bold_cell),
            Paragraph("<b>Product Description & Serial Number</b>", bold_cell),
            Paragraph("<b>Qty</b>", bold_cell),
            Paragraph("<b>Unit Price</b>", bold_cell),
            Paragraph("<b>Line Total</b>", bold_cell)
        ]
    ]

    for idx, item in enumerate(sale.items.all(), 1):
        desc = Paragraph(f"<b>{item.product.name}</b>" + (f"<br/><font color='#2563eb' size=8>SN: {item.serial_number}</font>" if item.serial_number else ""), item_title)
        item_rows.append([
            Paragraph(str(idx), cell_text),
            desc,
            Paragraph(str(item.quantity), cell_text),
            Paragraph(f"${item.unit_price:,.2f}", cell_text),
            Paragraph(f"<b>${item.total_price:,.2f}</b>", bold_cell)
        ])

    items_table = Table(item_rows, colWidths=[25, 270, 45, 95, 97])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    # 4. Total Calculation Box
    total_data = [
        [Paragraph("<b>TOTAL DUE:</b>", ParagraphStyle('TotalLabel', parent=bold_cell, alignment=2, fontSize=12)),
         Paragraph(f"<b>${sale.total_amount:,.2f}</b>", ParagraphStyle('TotalVal', parent=bold_cell, alignment=2, fontSize=14, textColor=colors.HexColor('#059669')))]
    ]
    total_table = Table(total_data, colWidths=[400, 132])
    total_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 20))

    # 5. Footer & Warranty
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=5, spaceAfter=10))
    footer_text = f"{settings_obj.receipt_footer_note}<br/>All products are inspected and verified by {settings_obj.company_name}. Keep receipt for warranty validation."
    elements.append(Paragraph(footer_text, ParagraphStyle('FooterStyle', parent=subtitle_style, alignment=1, fontSize=8, leading=11)))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{sale.invoice_number}.pdf"'
    return response


# ==============================================================================
# CUSTOMERS CRUD
# ==============================================================================

def customer_list_view(request):
    """Render full page for Customers."""
    queryset = Customer.objects.all().order_by('name')
    paginator = Paginator(queryset, 10)
    customers = paginator.page(1)
    return render(request, 'customers/customer_list.html', {
        'customers': customers,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def customer_table_partial(request):
    """Returns Customer table body and pagination partial HTML."""
    query = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)
    queryset = Customer.objects.all().order_by('name')

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(queryset, 10)
    try:
        customers = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        customers = paginator.page(1)

    return render(request, 'customers/partials/customer_table.html', {
        'customers': customers,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def customer_add_modal(request):
    """Return Add Customer modal partial."""
    return render(request, 'customers/partials/customer_add_modal.html')


def customer_edit_modal(request, pk):
    """Return Edit Customer modal partial."""
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'customers/partials/customer_edit_modal.html', {
        'customer': customer
    })


def customer_detail_modal(request, pk):
    """Return Customer Detail modal with sales history."""
    customer = get_object_or_404(Customer.objects.prefetch_related('sales__items__product'), pk=pk)
    return render(request, 'customers/partials/customer_detail_modal.html', {
        'customer': customer
    })


@require_POST
def customer_create(request):
    """Create customer from raw POST data."""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    errors = validate_customer(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Validation Failed",
                message="Please resolve the errors highlighted below.",
                errors=errors
            )
        return redirect('sales:customer_list')

    customer = Customer.objects.create(
        name=request.POST.get('name', '').strip(),
        phone=request.POST.get('phone', '').strip(),
        email=request.POST.get('email', '').strip(),
        address=request.POST.get('address', '').strip(),
        created_by=request.user if request.user.is_authenticated else None
    )

    if is_ajax:
        return success_response(
            title="Customer Created",
            message=f'Customer "{customer.name}" created successfully.',
            data={"customer_id": customer.pk, "name": customer.name, "phone": customer.phone}
        )
    return redirect('sales:customer_list')


@require_POST
def customer_update(request, pk):
    """Update customer from raw POST data."""
    customer = get_object_or_404(Customer, pk=pk)
    errors = validate_customer(request.POST, instance=customer)
    if errors:
        return error_response(
            title="Validation Failed",
            message="Please resolve the errors highlighted below.",
            errors=errors
        )

    customer.name = request.POST.get('name', '').strip()
    customer.phone = request.POST.get('phone', '').strip()
    customer.email = request.POST.get('email', '').strip()
    customer.address = request.POST.get('address', '').strip()
    customer.save()

    return success_response(
        title="Customer Updated",
        message=f'Customer "{customer.name}" updated successfully.',
        data={"customer_id": customer.pk}
    )


@require_POST
def customer_delete(request, pk):
    """Delete a customer record."""
    if request.user.is_authenticated and not (request.user.is_admin_role() or request.user.is_manager_role()):
        return permission_denied_response(
            title="Access Denied",
            message="Only Administrators or Managers are authorized to delete customers."
        )

    customer = get_object_or_404(Customer, pk=pk)
    if customer.sales.exists():
        return error_response(
            title="Cannot Delete",
            message=f'Customer "{customer.name}" has recorded sales and cannot be deleted.'
        )

    name = customer.name
    customer.delete()
    return success_response(
        title="Customer Deleted",
        message=f'Customer "{name}" was removed.'
    )
