"""
Function-Based Views for Business Expenses and Expense Categories.
Strictly zero Django Forms, 100% FBVs, uniform JSON envelope responses.
"""

from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum
from django.utils import timezone

from .models import Expense, ExpenseCategory
from core.responses import success_response, error_response, permission_denied_response
from core.validators import _parse_decimal, _parse_custom_date


# ==============================================================================
# EXPENSES LIST & TABLE
# ==============================================================================

def sync_recurring_expenses(user=None):
    """
    Check for categories configured as recurring and automatically generate
    scheduled expense records if due.
    """
    from datetime import date
    today = timezone.now().date()
    recurring_cats = ExpenseCategory.objects.filter(is_recurring=True, default_amount__gt=0)
    for cat in recurring_cats:
        last = cat.last_recurring_date
        is_due = False
        if not last:
            is_due = True
        elif cat.recurring_interval == 'DAILY' and today > last:
            is_due = True
        elif cat.recurring_interval == 'WEEKLY' and (today - last).days >= 7:
            is_due = True
        elif cat.recurring_interval == 'MONTHLY' and (today.year > last.year or (today.year == last.year and today.month > last.month)):
            is_due = True
        elif cat.recurring_interval == 'YEARLY' and today.year > last.year:
            is_due = True

        if is_due:
            Expense.objects.create(
                title=f"Recurring: {cat.name}",
                category=cat,
                amount=cat.default_amount,
                date=today,
                payment_method='Bank Transfer',
                notes=f"Auto-generated scheduled {cat.recurring_interval.lower()} expense",
                recorded_by=user
            )
            cat.last_recurring_date = today
            cat.save(update_fields=['last_recurring_date'])


def expense_list_view(request):
    """Render full shell for Expenses page."""
    sync_recurring_expenses(request.user)
    categories = ExpenseCategory.objects.all().order_by('name')
    queryset = Expense.objects.select_related('category', 'recorded_by').all().order_by('-date', '-created_at')
    
    total_spent = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    this_month_start = timezone.now().date().replace(day=1)
    month_spent = queryset.filter(date__gte=this_month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    paginator = Paginator(queryset, 10)
    expenses = paginator.page(1)
    return render(request, 'expenses/expense_list.html', {
        'categories': categories,
        'expenses': expenses,
        'paginator': paginator,
        'total_count': paginator.count,
        'total_spent': total_spent,
        'month_spent': month_spent,
    })


def expense_table_partial(request):
    """Filterable partial for Expenses."""
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    from_date = request.GET.get('from_date', '').strip()
    to_date = request.GET.get('to_date', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = Expense.objects.select_related('category', 'recorded_by').all().order_by('-date', '-created_at')

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(reference_number__icontains=query) |
            Q(notes__icontains=query)
        )
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if from_date:
        d = _parse_custom_date(from_date)
        if d: queryset = queryset.filter(date__gte=d)
    if to_date:
        d = _parse_custom_date(to_date)
        if d: queryset = queryset.filter(date__lte=d)

    paginator = Paginator(queryset, 10)
    try:
        expenses = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        expenses = paginator.page(1)

    return render(request, 'expenses/partials/expense_table.html', {
        'expenses': expenses,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def expense_add_modal(request):
    """Return Record Expense modal HTML partial."""
    categories = ExpenseCategory.objects.all().order_by('name')
    return render(request, 'expenses/partials/expense_add_modal.html', {
        'categories': categories,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })


@require_POST
def expense_create(request):
    """Records a new business expense."""
    title = request.POST.get('title', '').strip()
    category_id = request.POST.get('category')
    new_category_name = request.POST.get('new_category_name', '').strip()
    amount_raw = request.POST.get('amount')
    date_raw = request.POST.get('date')
    payment_method = request.POST.get('payment_method', 'Cash')
    ref_num = request.POST.get('reference_number', '').strip()
    notes = request.POST.get('notes', '').strip()

    errors = {}
    if not title:
        errors['title'] = "Expense description/title is required."
    
    amount = _parse_decimal(amount_raw)
    if amount is None or amount <= Decimal('0.00'):
        errors['amount'] = "Please enter a valid positive expense amount."

    date_obj = _parse_custom_date(date_raw) if date_raw else timezone.now().date()

    category = None
    if new_category_name:
        category, _ = ExpenseCategory.objects.get_or_create(name=new_category_name)
    elif category_id:
        try:
            category = ExpenseCategory.objects.get(pk=category_id)
        except ExpenseCategory.DoesNotExist:
            errors['category'] = "Selected category does not exist."
    else:
        errors['category'] = "Please select or create an expense category."

    if errors:
        return error_response(title="Validation Error", message="Please correct errors below.", errors=errors)

    expense = Expense.objects.create(
        title=title,
        category=category,
        amount=amount,
        date=date_obj,
        payment_method=payment_method,
        reference_number=ref_num,
        notes=notes,
        recorded_by=request.user if request.user.is_authenticated else None
    )

    return success_response(
        title="Expense Recorded",
        message=f'Recorded expense "{expense.title}" of ${expense.amount:,.2f}.',
        data={'expense_id': expense.id}
    )


def expense_edit_modal(request, pk):
    """Return Edit Expense modal HTML partial."""
    expense = get_object_or_404(Expense.objects.select_related('category'), pk=pk)
    categories = ExpenseCategory.objects.all().order_by('name')
    return render(request, 'expenses/partials/expense_edit_modal.html', {
        'expense': expense,
        'categories': categories,
    })


@require_POST
def expense_update(request, pk):
    """Updates an existing business expense."""
    expense = get_object_or_404(Expense, pk=pk)
    title = request.POST.get('title', '').strip()
    category_id = request.POST.get('category')
    amount_raw = request.POST.get('amount')
    date_raw = request.POST.get('date')
    payment_method = request.POST.get('payment_method', expense.payment_method)
    ref_num = request.POST.get('reference_number', '').strip()
    notes = request.POST.get('notes', '').strip()

    errors = {}
    if not title:
        errors['title'] = "Expense title is required."
    amount = _parse_decimal(amount_raw)
    if amount is None or amount <= Decimal('0.00'):
        errors['amount'] = "Please enter a valid amount."

    category = get_object_or_404(ExpenseCategory, pk=category_id) if category_id else expense.category

    if errors:
        return error_response(title="Validation Error", message="Please fix errors below.", errors=errors)

    expense.title = title
    expense.category = category
    expense.amount = amount
    if date_raw:
        d = _parse_custom_date(date_raw)
        if d: expense.date = d
    expense.payment_method = payment_method
    expense.reference_number = ref_num
    expense.notes = notes
    expense.save()

    return success_response(
        title="Expense Updated",
        message=f'Expense "{expense.title}" updated successfully.',
        data={'expense_id': expense.id}
    )


@require_POST
def expense_delete(request, pk):
    """Deletes an expense record."""
    expense = get_object_or_404(Expense, pk=pk)
    title = expense.title
    amount = expense.amount
    expense.delete()
    return success_response(
        title="Expense Deleted",
        message=f'Expense "{title}" (${amount:,.2f}) deleted.'
    )


def expense_detail_modal(request, pk):
    """Return Expense Detail modal HTML partial."""
    expense = get_object_or_404(Expense.objects.select_related('category', 'recorded_by'), pk=pk)
    return render(request, 'expenses/partials/expense_detail_modal.html', {'expense': expense})


# ==============================================================================
# EXPENSE CATEGORIES (DEDICATED TABLE AS REQUESTED)
# ==============================================================================

def expense_category_list_view(request):
    """Render full shell for Expense Categories."""
    queryset = ExpenseCategory.objects.all().order_by('name')
    paginator = Paginator(queryset, 10)
    categories = paginator.page(1)
    return render(request, 'expenses/categories/category_list.html', {
        'categories': categories,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def expense_category_table_partial(request):
    """Filterable partial for Expense Categories."""
    query = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    queryset = ExpenseCategory.objects.all().order_by('name')
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))

    paginator = Paginator(queryset, 10)
    try:
        categories = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        categories = paginator.page(1)

    return render(request, 'expenses/categories/category_table.html', {
        'categories': categories,
        'paginator': paginator,
        'total_count': paginator.count,
    })


def expense_category_add_modal(request):
    """Return Add Expense Category modal partial."""
    return render(request, 'expenses/categories/category_add_modal.html')


@require_POST
def expense_category_create(request):
    """Creates a new expense category."""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    default_amount_raw = request.POST.get('default_amount', '0.00')
    is_recurring = request.POST.get('is_recurring') in ['true', '1', 'on', True]
    recurring_interval = request.POST.get('recurring_interval', 'MONTHLY').upper()

    if not name:
        return error_response(title="Validation Error", message="Category name is required.")
    if ExpenseCategory.objects.filter(name__iexact=name).exists():
        return error_response(title="Duplicate Category", message=f'Expense category "{name}" already exists.')

    default_amount = _parse_decimal(default_amount_raw, Decimal('0.00'))

    cat = ExpenseCategory.objects.create(
        name=name,
        description=description,
        default_amount=default_amount,
        is_recurring=is_recurring,
        recurring_interval=recurring_interval
    )
    return success_response(
        title="Category Created",
        message=f'Expense category "{cat.name}" created successfully.',
        data={'category_id': cat.id, 'name': cat.name}
    )


def expense_category_edit_modal(request, pk):
    """Return Edit Expense Category modal partial."""
    cat = get_object_or_404(ExpenseCategory, pk=pk)
    return render(request, 'expenses/categories/category_edit_modal.html', {'category': cat})


@require_POST
def expense_category_update(request, pk):
    """Updates an expense category."""
    cat = get_object_or_404(ExpenseCategory, pk=pk)
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    default_amount_raw = request.POST.get('default_amount', '0.00')
    is_recurring = request.POST.get('is_recurring') in ['true', '1', 'on', True]
    recurring_interval = request.POST.get('recurring_interval', 'MONTHLY').upper()

    if not name:
        return error_response(title="Validation Error", message="Category name is required.")
    if ExpenseCategory.objects.filter(name__iexact=name).exclude(pk=pk).exists():
        return error_response(title="Duplicate Category", message=f'Expense category "{name}" already exists.')

    cat.name = name
    cat.description = description
    cat.default_amount = _parse_decimal(default_amount_raw, Decimal('0.00'))
    cat.is_recurring = is_recurring
    cat.recurring_interval = recurring_interval
    cat.save()

    return success_response(
        title="Category Updated",
        message=f'Expense category "{cat.name}" updated successfully.',
        data={'category_id': cat.id}
    )


@require_POST
def expense_category_delete(request, pk):
    """Deletes an expense category."""
    cat = get_object_or_404(ExpenseCategory, pk=pk)
    if cat.expenses.exists():
        return error_response(
            title="Cannot Delete",
            message=f'Category "{cat.name}" has {cat.expenses.count()} recorded expenses. Reassign or delete them first.'
        )
    name = cat.name
    cat.delete()
    return success_response(title="Category Deleted", message=f'Expense category "{name}" was deleted.')
