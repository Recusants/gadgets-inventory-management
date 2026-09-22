"""
Function-Based Views for Products, Inventory, Stock Batches, and Categories.
Strictly zero Django Forms, 100% FBVs, uniform JSON envelope responses.
"""

import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from .models import Product, Stock, StockBatch, Category, ProductStatus, Supplier
from core.validators import validate_product, validate_receive_invoice, validate_category, validate_supplier, _parse_decimal, _parse_custom_date
from core.responses import success_response, error_response, permission_denied_response
from core.decorators import admin_required, manager_or_admin_required, ajax_required


# ==============================================================================
# PRODUCTS & INVENTORY
# ==============================================================================

def product_list_view(request):
    """
    Renders the Product / Inventory full page with initial table pre-rendered.
    Dynamic search, filters, and pagination continue via AJAX.
    """
    categories = Category.objects.all().order_by('name')
    queryset = Product.objects.select_related('category', 'stock', 'created_by').all().order_by('-created_at')
    paginator = Paginator(queryset, 10)
    products = paginator.page(1)
    return render(request, 'inventory/product_list.html', {
        'categories': categories,
        'products': products,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def product_table_partial(request):
    """
    Returns the table body and pagination partial HTML.
    Called via AJAX on page load, search typing, filter change, or pagination click.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Product.objects.select_related('category', 'stock', 'created_by').all().order_by('-created_at')

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(description__icontains=query)
        )

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if status_filter == 'in_stock':
        queryset = queryset.filter(stock__quantity_available__gt=0)
    elif status_filter == 'out_of_stock':
        queryset = queryset.filter(Q(stock__quantity_available=0) | Q(stock__isnull=True))
    elif status_filter == 'low_stock':
        queryset = queryset.filter(stock__quantity_available__gt=0, stock__quantity_available__lte=5)

    paginator = Paginator(queryset, 10)
    try:
        products = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        products = paginator.page(1)

    return render(request, 'inventory/partials/product_table.html', {
        'products': products,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def product_search_ajax(request):
    """
    Limited search endpoint for POS checkout and selectors.
    Returns maximum 10 matches as clean JSON.
    """
    query = request.GET.get('q', '').strip()
    qs = Product.objects.select_related('category', 'stock').all()
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(serial_number__icontains=query)
        )
    
    results = []
    for p in qs[:10]:
        results.append({
            'id': p.id,
            'name': p.name,
            'category': p.category.name if p.category else '',
            'selling_price': float(p.current_selling_price),
            'available_quantity': p.available_quantity,
        })
    return JsonResponse({'status': 'success', 'results': results})


def product_add_modal(request):
    """Returns the Add Product modal HTML partial."""
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/partials/product_add_modal.html', {
        'categories': categories,
    })


def product_edit_modal(request, pk):
    """Returns the Edit Product modal HTML partial pre-filled with data."""
    product = get_object_or_404(Product.objects.select_related('category', 'stock'), pk=pk)
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/partials/product_edit_modal.html', {
        'product': product,
        'categories': categories,
    })


def product_detail_modal(request, pk):
    """Returns the Product Detail modal HTML partial with active batches."""
    product = get_object_or_404(Product.objects.select_related('category', 'stock', 'created_by').prefetch_related('batches'), pk=pk)
    return render(request, 'inventory/partials/product_detail_modal.html', {
        'product': product,
    })


@require_POST
def product_create(request):
    """Creates a new generic product definition with default Stock record."""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    errors = validate_product(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Validation Failed",
                message="Please resolve the errors highlighted below.",
                errors=errors
            )
        return redirect('inventory:product_list')

    category = Category.objects.get(pk=request.POST.get('category'))
    selling_price = _parse_decimal(request.POST.get('selling_price')) or Decimal('0.00')

    product = Product.objects.create(
        name=request.POST.get('name', '').strip(),
        category=category,
        sku=request.POST.get('sku', '').strip(),
        size=request.POST.get('size', '').strip(),
        description=request.POST.get('description', '').strip(),
        created_by=request.user if request.user.is_authenticated else None
    )

    stock, _ = Stock.objects.get_or_create(product=product)
    stock.selling_price = selling_price
    stock.save()

    # If initial stock intake was entered in the same form
    init_qty = request.POST.get('initial_quantity')
    init_cost = request.POST.get('initial_cost_price')
    if init_qty and init_cost:
        try:
            iq = int(init_qty)
            ic = _parse_decimal(init_cost)
            if iq > 0 and ic is not None:
                StockBatch.objects.create(
                    product=product,
                    stock=stock,
                    supplier_invoice_number=request.POST.get('supplier_invoice_number', 'INIT-INTAKE').strip(),
                    supplier_name=request.POST.get('supplier_name', '').strip(),
                    cost_price=ic,
                    quantity_received=iq,
                    quantity_remaining=iq,
                    is_active=True,
                    created_by=request.user if request.user.is_authenticated else None
                )
                stock.recalculate_quantity()
        except Exception:
            pass

    if is_ajax:
        return success_response(
            title="Product Created",
            message=f'Product "{product.name}" created successfully.',
            data={"product_id": product.pk, "name": product.name, "selling_price": str(stock.selling_price)}
        )
    return redirect('inventory:product_list')


@require_POST
def product_update(request, pk):
    """Updates an existing product record and selling price."""
    product = get_object_or_404(Product, pk=pk)
    errors = validate_product(request.POST, instance=product)
    if errors:
        return error_response(
            title="Validation Failed",
            message="Please resolve the errors highlighted below.",
            errors=errors
        )

    category = Category.objects.get(pk=request.POST.get('category'))
    product.name = request.POST.get('name', '').strip()
    product.sku = request.POST.get('sku', '').strip()
    product.size = request.POST.get('size', '').strip()
    product.description = request.POST.get('description', '').strip()
    product.category = category
    product.save()

    selling_price = _parse_decimal(request.POST.get('selling_price'))
    if selling_price is not None:
        stock, _ = Stock.objects.get_or_create(product=product)
        stock.selling_price = selling_price
        stock.save()


    return success_response(
        title="Product Updated",
        message=f'"{product.name}" updated successfully.',
        data={"product_id": product.pk}
    )


@require_POST
def product_delete(request, pk):
    """Deletes a product record."""
    if request.user.is_authenticated and not (request.user.is_admin_role() or request.user.is_manager_role()):
        return permission_denied_response(
            title="Access Denied",
            message="Only Administrators or Managers are authorized to delete inventory items."
        )

    product = get_object_or_404(Product, pk=pk)
    if product.sale_items.exists():
        return error_response(
            title="Cannot Delete",
            message=f'Product "{product.name}" has completed sales records and cannot be deleted.'
        )

    name = product.name
    product.delete()
    return success_response(
        title="Product Deleted",
        message=f'Product "{name}" was successfully removed.'
    )


# ==============================================================================
# RECEIVE INVOICE & STOCK BATCHES
# ==============================================================================

def receive_invoice_modal(request):
    """Returns modal HTML for receiving a supplier invoice (3-tab wizard with searchable selects)."""
    products = Product.objects.select_related('stock').all().order_by('name')
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'inventory/partials/receive_invoice_modal.html', {
        'products': products,
        'suppliers': suppliers,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })


@require_POST
def receive_invoice_save(request):
    """
    Receives an incoming supplier invoice (supports multi-item 3-tab wizard or single item),
    creates FIFO stock batches, updates selling prices, recalculates stock, and links supplier.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    items_json = request.POST.get('items_json', '').strip()

    if items_json:
        try:
            items = json.loads(items_json)
        except Exception:
            return error_response(title="Invalid Data", message="Invalid items format.")

        if not items:
            return error_response(title="No Items", message="Please add at least one product item to the invoice.")

        supplier_id = request.POST.get('supplier_id') or request.POST.get('supplier')
        supplier_ref = None
        if supplier_id:
            supplier_ref = Supplier.objects.filter(pk=supplier_id).first()

        supplier_name = (supplier_ref.name if supplier_ref else request.POST.get('supplier_name', '').strip()) or 'Direct Supplier'
        invoice_num = request.POST.get('supplier_invoice_number', '').strip() or f"INV-{timezone.now().strftime('%y%m%d%H%M')}"
        date_received = _parse_custom_date(request.POST.get('date_received')) or timezone.now().date()
        notes = request.POST.get('notes', '').strip()

        created_batches = []
        total_qty = 0
        for it in items:
            p_id = it.get('product_id')
            p_qty = int(it.get('quantity', 1))
            p_cost = _parse_decimal(it.get('cost_price', '0')) or Decimal('0.00')
            p_sell = _parse_decimal(it.get('selling_price', '0'))

            product = Product.objects.filter(pk=p_id).first()
            if not product or p_qty <= 0:
                continue

            stock, _ = Stock.objects.get_or_create(product=product)
            if p_sell is not None and p_sell > Decimal('0.00'):
                stock.selling_price = p_sell
                stock.save(update_fields=['selling_price', 'updated_at'])

            batch = StockBatch.objects.create(
                product=product,
                stock=stock,
                supplier_ref=supplier_ref,
                supplier_invoice_number=invoice_num,
                supplier_name=supplier_name,
                date_received=date_received,
                cost_price=p_cost,
                quantity_received=p_qty,
                quantity_remaining=p_qty,
                is_active=True,
                notes=notes,
                created_by=request.user if request.user.is_authenticated else None
            )
            stock.recalculate_quantity()
            created_batches.append(batch)
            total_qty += p_qty

        return success_response(
            title="Invoice Received",
            message=f"Received {len(created_batches)} products ({total_qty} units total) under Invoice '{invoice_num}'.",
            data={"items_count": len(created_batches), "total_qty": total_qty, "invoice_number": invoice_num}
        )

    # Fallback to single item receiving
    errors = validate_receive_invoice(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Validation Failed",
                message="Please resolve the errors highlighted below.",
                errors=errors
            )
        return redirect('inventory:product_list')

    product = Product.objects.get(pk=request.POST.get('product') or request.POST.get('product_id'))
    invoice_num = request.POST.get('supplier_invoice_number', '').strip()
    supplier_id = request.POST.get('supplier_id') or request.POST.get('supplier')
    supplier_ref = Supplier.objects.filter(pk=supplier_id).first() if supplier_id else None
    supplier_name = (supplier_ref.name if supplier_ref else request.POST.get('supplier_name', '').strip()) or 'Direct Supplier'
    qty = int(request.POST.get('quantity') or request.POST.get('quantity_received'))
    cost_price = _parse_decimal(request.POST.get('cost_price') or request.POST.get('amount_bought'))
    selling_price = _parse_decimal(request.POST.get('selling_price') or request.POST.get('amount_sold'))
    date_received = _parse_custom_date(request.POST.get('date_received')) or timezone.now().date()
    notes = request.POST.get('notes', '').strip()

    stock, _ = Stock.objects.get_or_create(product=product)
    if selling_price is not None and selling_price > Decimal('0.00'):
        stock.selling_price = selling_price
        stock.save(update_fields=['selling_price', 'updated_at'])

    batch = StockBatch.objects.create(
        product=product,
        stock=stock,
        supplier_ref=supplier_ref,
        supplier_invoice_number=invoice_num,
        supplier_name=supplier_name,
        date_received=date_received,
        cost_price=cost_price,
        quantity_received=qty,
        quantity_remaining=qty,
        is_active=True,
        notes=notes,
        created_by=request.user if request.user.is_authenticated else None
    )

    stock.recalculate_quantity()

    if is_ajax:
        return success_response(
            title="Invoice Received",
            message=f"Received {qty} units of '{product.name}' into Batch #{batch.id}.",
            data={
                "batch_id": batch.id,
                "product_name": product.name,
                "quantity_available": stock.quantity_available,
                "selling_price": str(stock.selling_price)
            }
        )
    return redirect('inventory:product_list')


def batch_list_view(request):
    """View active and historical stock batches."""
    batches = StockBatch.objects.select_related('product__category').all().order_by('-date_received', '-id')
    return render(request, 'inventory/batch_list.html', {'batches': batches})


# ==============================================================================
# CATEGORIES
# ==============================================================================

def category_list_view(request):
    """Render the Categories page."""
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/categories/category_list.html', {
        'categories': categories,
        'total_count': categories.count(),
    })


def category_table_partial(request):
    """Returns Category table body partial HTML."""
    query = request.GET.get('q', '').strip()
    queryset = Category.objects.all().order_by('name')
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))

    return render(request, 'inventory/categories/category_table.html', {
        'categories': queryset,
        'total_count': queryset.count(),
    })


def category_add_modal(request):
    """Return Add Category modal HTML partial."""
    return render(request, 'inventory/categories/category_add_modal.html')


def category_edit_modal(request, pk):
    """Return Edit Category modal HTML partial."""
    category = get_object_or_404(Category, pk=pk)
    return render(request, 'inventory/categories/category_edit_modal.html', {
        'category': category
    })



@require_POST
def category_create(request):
    """Creates a new category from raw POST data."""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    errors = validate_category(request.POST)
    if errors:
        if is_ajax:
            return error_response(
                title="Validation Failed",
                message="Please resolve the errors highlighted below.",
                errors=errors
            )
        return redirect('inventory:category_list')

    category = Category.objects.create(
        name=request.POST.get('name', '').strip(),
        description=request.POST.get('description', '').strip()
    )

    if is_ajax:
        return success_response(
            title="Category Created",
            message=f'Category "{category.name}" created successfully.',
            data={"category_id": category.pk, "name": category.name}
        )
    return redirect('inventory:category_list')


@require_POST
def category_update(request, pk):
    """Updates an existing category."""
    category = get_object_or_404(Category, pk=pk)
    errors = validate_category(request.POST, instance=category)
    if errors:
        return error_response(
            title="Validation Failed",
            message="Please resolve the errors highlighted below.",
            errors=errors
        )

    category.name = request.POST.get('name', '').strip()
    category.description = request.POST.get('description', '').strip()
    category.save()

    return success_response(
        title="Category Updated",
        message=f'Category "{category.name}" updated successfully.',
        data={"category_id": category.pk}
    )


@require_POST
def category_delete(request, pk):
    """Deletes a category."""
    if request.user.is_authenticated and not (request.user.is_admin_role() or request.user.is_manager_role()):
        return permission_denied_response(
            title="Access Denied",
            message="Only Administrators or Managers are authorized to delete categories."
        )

    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        return error_response(
            title="Cannot Delete Category",
            message=f'Category "{category.name}" contains {category.products.count()} products. Reassign them first.'
        )

    name = category.name
    category.delete()
    return success_response(
        title="Category Deleted",
        message=f'Category "{name}" was successfully deleted.'
    )


def stock_price_modal(request, pk):
    """Returns the quick edit selling price modal partial."""
    stock = get_object_or_404(Stock.objects.select_related('product'), pk=pk)
    return render(request, 'inventory/partials/stock_price_modal.html', {'stock': stock})


@require_POST
def stock_price_update(request, pk):
    """Updates selling price of a Stock record."""
    stock = get_object_or_404(Stock.objects.select_related('product'), pk=pk)
    new_price = _parse_decimal(request.POST.get('selling_price'))
    if new_price is None or new_price < Decimal('0.00'):
        return error_response(
            title="Validation Error",
            message="Please enter a valid positive selling price.",
            errors={'selling_price': 'Invalid selling price.'}
        )
    stock.selling_price = new_price
    stock.save(update_fields=['selling_price', 'updated_at'])
    return success_response(
        title="Selling Price Updated",
        message=f"Selling price for '{stock.product.name}' updated to ${new_price:,.2f}.",
        data={'stock_id': stock.id, 'selling_price': str(stock.selling_price)}
    )


# ==============================================================================
# DEDICATED STOCK PAGE (PRICING & VALUATION)
# ==============================================================================

def stock_list_view(request):
    """
    Renders the dedicated Stock Page where selling prices can be edited directly.
    Shows available quantities aggregated from active batches.
    """
    categories = Category.objects.all().order_by('name')
    queryset = Stock.objects.select_related('product__category').all().order_by('product__name')
    paginator = Paginator(queryset, 10)
    stocks = paginator.page(1)
    return render(request, 'inventory/stock_list.html', {
        'categories': categories,
        'stocks': stocks,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def stock_table_partial(request):
    """Filterable partial for Stock Page."""
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Stock.objects.select_related('product__category').all().order_by('product__name')
    if query:
        queryset = queryset.filter(
            Q(product__name__icontains=query) |
            Q(product__sku__icontains=query)
        )
    if category_id:
        queryset = queryset.filter(product__category_id=category_id)
    if status_filter == 'In Stock':
        queryset = queryset.filter(quantity_available__gt=5)
    elif status_filter == 'Low Stock':
        queryset = queryset.filter(quantity_available__gt=0, quantity_available__lte=5)
    elif status_filter == 'Out of Stock':
        queryset = queryset.filter(quantity_available=0)

    paginator = Paginator(queryset, 10)
    try:
        stocks = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        stocks = paginator.page(1)

    return render(request, 'inventory/partials/stock_table.html', {
        'stocks': stocks,
        'paginator': paginator,
        'total_count': paginator.count,
    })


# ==============================================================================
# BATCH DETAILS & EDIT QUANTITIES
# ==============================================================================

def batch_detail_modal(request, pk):
    """Returns modal with complete information on a specific batch."""
    batch = get_object_or_404(StockBatch.objects.select_related('product__category', 'created_by'), pk=pk)
    return render(request, 'inventory/partials/batch_detail_modal.html', {'batch': batch})


def batch_quantity_edit_modal(request, pk):
    """Returns modal to edit/adjust batch quantities."""
    batch = get_object_or_404(StockBatch.objects.select_related('product'), pk=pk)
    return render(request, 'inventory/partials/batch_quantity_edit_modal.html', {'batch': batch})


@require_POST
def batch_quantity_update(request, pk):
    """
    Updates quantities for a specific batch and recalculates available stock.
    """
    batch = get_object_or_404(StockBatch.objects.select_related('product'), pk=pk)
    try:
        qty_rem = int(request.POST.get('quantity_remaining', batch.quantity_remaining))
        qty_rec = int(request.POST.get('quantity_received', batch.quantity_received))
        if qty_rem < 0 or qty_rec < 0:
            return error_response(title="Invalid Quantity", message="Quantities cannot be negative.")
        if qty_rem > qty_rec:
            return error_response(title="Invalid Quantity", message="Quantity remaining cannot exceed quantity received.")
    except (ValueError, TypeError):
        return error_response(title="Invalid Quantity", message="Please enter valid integer quantities.")

    notes = request.POST.get('notes', '').strip()
    batch.quantity_remaining = qty_rem
    batch.quantity_received = qty_rec
    batch.is_active = qty_rem > 0
    if notes:
        batch.notes = f"{batch.notes}\n[Adjustment] {notes}".strip()
    batch.save()

    # Recalculate associated Stock quantity
    stock = getattr(batch.product, 'stock', None)
    if not stock:
        stock, _ = Stock.objects.get_or_create(product=batch.product)
    stock.recalculate_quantity()

    return success_response(
        title="Batch Quantity Updated",
        message=f"Batch #{batch.id} quantities updated. Current available stock is {stock.quantity_available}.",
        data={'batch_id': batch.id, 'quantity_remaining': batch.quantity_remaining}
    )


# ==============================================================================
# INVOICES PAGE (SHOWS ALL INVOICES)
# ==============================================================================

def invoice_list_view(request):
    """
    Renders dedicated Invoices Page showing all received invoices.
    """
    batches = StockBatch.objects.select_related('product').all().order_by('-date_received', '-id')
    invoices_dict = {}
    for b in batches:
        inv = b.supplier_invoice_number or f"BATCH-{b.id}"
        if inv not in invoices_dict:
            invoices_dict[inv] = {
                'invoice_number': inv,
                'supplier_name': b.supplier_name or 'Direct Supplier',
                'date_received': b.date_received,
                'batch_count': 0,
                'total_qty_received': 0,
                'total_qty_remaining': 0,
                'total_cost': Decimal('0.00'),
                'batches': []
            }
        invoices_dict[inv]['batch_count'] += 1
        invoices_dict[inv]['total_qty_received'] += b.quantity_received
        invoices_dict[inv]['total_qty_remaining'] += b.quantity_remaining
        invoices_dict[inv]['total_cost'] += (b.cost_price * b.quantity_received)
        invoices_dict[inv]['batches'].append(b)

    invoice_list = list(invoices_dict.values())
    paginator = Paginator(invoice_list, 10)
    page_obj = paginator.page(1)
    return render(request, 'inventory/invoice_list.html', {
        'invoices': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def invoice_table_partial(request):
    """Filterable partial for Invoices Page."""
    query = request.GET.get('q', '').strip().lower()
    page_num = request.GET.get('page', 1)

    batches = StockBatch.objects.select_related('product').all().order_by('-date_received', '-id')
    invoices_dict = {}
    for b in batches:
        inv = b.supplier_invoice_number or f"BATCH-{b.id}"
        if inv not in invoices_dict:
            invoices_dict[inv] = {
                'invoice_number': inv,
                'supplier_name': b.supplier_name or 'Direct Supplier',
                'date_received': b.date_received,
                'batch_count': 0,
                'total_qty_received': 0,
                'total_qty_remaining': 0,
                'total_cost': Decimal('0.00'),
                'batches': []
            }
        invoices_dict[inv]['batch_count'] += 1
        invoices_dict[inv]['total_qty_received'] += b.quantity_received
        invoices_dict[inv]['total_qty_remaining'] += b.quantity_remaining
        invoices_dict[inv]['total_cost'] += (b.cost_price * b.quantity_received)
        invoices_dict[inv]['batches'].append(b)

    invoice_list = list(invoices_dict.values())
    if query:
        invoice_list = [
            inv for inv in invoice_list
            if query in inv['invoice_number'].lower() or query in inv['supplier_name'].lower()
        ]

    paginator = Paginator(invoice_list, 10)
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    return render(request, 'inventory/partials/invoice_table.html', {
        'invoices': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def invoice_detail_modal(request, invoice_number):
    """Modal showing all batch items on a specific invoice."""
    batches = StockBatch.objects.filter(
        Q(supplier_invoice_number=invoice_number) | Q(id__icontains=invoice_number.replace('BATCH-', ''))
    ).select_related('product__category')
    if not batches.exists():
        batches = StockBatch.objects.filter(supplier_invoice_number__iexact=invoice_number).select_related('product__category')

    first_b = batches.first()
    supplier = first_b.supplier_name if first_b else 'Direct Supplier'
    date_rec = first_b.date_received if first_b else timezone.now().date()
    total_cost = sum(b.cost_price * b.quantity_received for b in batches)
    total_qty = sum(b.quantity_received for b in batches)
    total_rem = sum(b.quantity_remaining for b in batches)

    return render(request, 'inventory/partials/invoice_detail_modal.html', {
        'invoice_number': invoice_number,
        'supplier_name': supplier,
        'date_received': date_rec,
        'total_cost': total_cost,
        'total_qty': total_qty,
        'total_rem': total_rem,
        'batches': batches,
    })


# ==============================================================================
# SUPPLIERS (DEDICATED CRUD TABLE)
# ==============================================================================

def supplier_list_view(request):
    """Render full shell for Suppliers page."""
    queryset = Supplier.objects.all().order_by('name')
    paginator = Paginator(queryset, 10)
    suppliers = paginator.page(1)
    return render(request, 'inventory/suppliers/supplier_list.html', {
        'suppliers': suppliers,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def supplier_table_partial(request):
    """Filterable partial for Suppliers."""
    query = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Supplier.objects.all().order_by('name')
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(queryset, 10)
    try:
        suppliers = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        suppliers = paginator.page(1)

    return render(request, 'inventory/suppliers/supplier_table.html', {
        'suppliers': suppliers,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def supplier_add_modal(request):
    """Return Add Supplier modal partial."""
    return render(request, 'inventory/suppliers/supplier_add_modal.html')


@require_POST
def supplier_create(request):
    """Creates a new supplier."""
    errors = validate_supplier(request.POST)
    if errors:
        return error_response(title="Validation Error", message="Please correct errors below.", errors=errors)

    supplier = Supplier.objects.create(
        name=request.POST.get('name', '').strip(),
        contact_person=request.POST.get('contact_person', '').strip(),
        phone=request.POST.get('phone', '').strip(),
        email=request.POST.get('email', '').strip(),
        address=request.POST.get('address', '').strip(),
        notes=request.POST.get('notes', '').strip(),
    )
    return success_response(
        title="Supplier Added",
        message=f'Supplier "{supplier.name}" created successfully.',
        data={'supplier_id': supplier.id, 'name': supplier.name}
    )


def supplier_edit_modal(request, pk):
    """Return Edit Supplier modal partial."""
    supplier = get_object_or_404(Supplier, pk=pk)
    return render(request, 'inventory/suppliers/supplier_edit_modal.html', {'supplier': supplier})


@require_POST
def supplier_update(request, pk):
    """Updates an existing supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)
    errors = validate_supplier(request.POST, instance=supplier)
    if errors:
        return error_response(title="Validation Error", message="Please correct errors below.", errors=errors)

    supplier.name = request.POST.get('name', '').strip()
    supplier.contact_person = request.POST.get('contact_person', '').strip()
    supplier.phone = request.POST.get('phone', '').strip()
    supplier.email = request.POST.get('email', '').strip()
    supplier.address = request.POST.get('address', '').strip()
    supplier.notes = request.POST.get('notes', '').strip()
    supplier.save()

    return success_response(
        title="Supplier Updated",
        message=f'Supplier "{supplier.name}" updated successfully.',
        data={'supplier_id': supplier.id}
    )


@require_POST
def supplier_delete(request, pk):
    """Deletes a supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)
    if supplier.batches.exists():
        return error_response(
            title="Cannot Delete",
            message=f'Supplier "{supplier.name}" has {supplier.batches.count()} linked invoice batches and cannot be deleted.'
        )
    name = supplier.name
    supplier.delete()
    return success_response(title="Supplier Deleted", message=f'Supplier "{name}" deleted successfully.')



