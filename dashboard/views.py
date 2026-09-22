"""
Function-Based Views for the 21 Void Technologies Dashboard.
Strictly zero Django Forms, 100% FBVs, Django ORM aggregations, 60s caching.
"""

from decimal import Decimal
import json
from django.shortcuts import render
from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from inventory.models import Product, Stock, StockBatch, Category
from sales.models import Sale, SaleItem
from expenses.models import Expense
from core.responses import success_response


def get_dashboard_metrics():
    """
    Computes system metrics using high-performance Django ORM aggregations.
    Cached for 60 seconds with automatic invalidation on Sale/Expense create/delete.
    """
    cached_metrics = cache.get('dashboard_stats')
    if cached_metrics:
        return cached_metrics

    today = timezone.now().date()

    # Product and Stock counts
    total_products = Product.objects.count()
    in_stock = Product.objects.filter(stock__quantity_available__gt=0).count()
    low_stock = Product.objects.filter(stock__quantity_available__gt=0, stock__quantity_available__lte=5).count()
    total_units_sold = SaleItem.objects.aggregate(total=Sum('quantity'))['total'] or 0

    # Sales aggregations
    sales_aggregations = Sale.objects.aggregate(
        total_revenue=Sum('total_amount'),
        total_cogs=Sum('total_cost'),
        gross_profit=Sum('total_profit')
    )

    # Expenses aggregations
    total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    today_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    gross_profit = sales_aggregations['gross_profit'] or Decimal('0.00')
    net_profit = gross_profit - total_expenses

    # Today's sales
    today_revenue = Sale.objects.filter(date_sold=today).aggregate(
        today_total=Sum('total_amount')
    )['today_total'] or Decimal('0.00')

    metrics = {
        'total_products': total_products,
        'in_stock': in_stock,
        'sold': total_units_sold,
        'low_stock': low_stock,
        'total_sales': sales_aggregations['total_revenue'] or Decimal('0.00'),
        'total_cost': sales_aggregations['total_cogs'] or Decimal('0.00'),
        'gross_profit': gross_profit,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'today_sales': today_revenue,
        'today_expenses': today_expenses,
    }

    cache.set('dashboard_stats', metrics, timeout=60)
    return metrics


def get_chart_data():
    """Builds historical trend and category breakdown for Chart.js."""
    today = timezone.now().date()
    
    # 1. Last 6 Months Revenue, Profit & Expense Trend
    month_labels = []
    revenue_data = []
    profit_data = []
    expense_data = []
    net_profit_data = []

    for i in range(5, -1, -1):
        # Approximate 30-day buckets
        start_date = today - timedelta(days=(i + 1) * 30)
        end_date = today - timedelta(days=i * 30)
        month_name = end_date.strftime('%b %Y')
        
        agg = Sale.objects.filter(date_sold__gt=start_date, date_sold__lte=end_date).aggregate(
            rev=Sum('total_amount'),
            prof=Sum('total_profit')
        )
        exp_tot = Expense.objects.filter(date__gt=start_date, date__lte=end_date).aggregate(
            tot=Sum('amount')
        )['tot'] or Decimal('0.00')

        rev_val = float(agg['rev'] or 0)
        prof_val = float(agg['prof'] or 0)
        exp_val = float(exp_tot)
        net_val = prof_val - exp_val

        month_labels.append(month_name)
        revenue_data.append(rev_val)
        profit_data.append(prof_val)
        expense_data.append(exp_val)
        net_profit_data.append(net_val)

    # 2. Inventory by Category Distribution
    categories = Category.objects.annotate(prod_count=Count('products')).filter(prod_count__gt=0).order_by('-prod_count')[:6]
    cat_labels = [c.name for c in categories] or ['General Equipment']
    cat_counts = [c.prod_count for c in categories] or [Product.objects.count()]

    return {
        'months': month_labels,
        'revenues': revenue_data,
        'profits': profit_data,
        'expenses': expense_data,
        'net_profits': net_profit_data,
        'categories': cat_labels,
        'category_counts': cat_counts,
        'cat_labels': cat_labels,
        'cat_counts': cat_counts
    }


def index(request):
    """
    Main dashboard controller.
    Fetches aggregated metrics, Chart.js payload, and recent sales/products.
    """
    metrics = get_dashboard_metrics()
    charts = get_chart_data()

    # Pre-render recent 5 sales and 5 products
    recent_sales = Sale.objects.select_related('customer', 'user').prefetch_related('items__product').order_by('-created_at')[:5]
    recent_products = Product.objects.select_related('category', 'stock').order_by('-created_at')[:5]

    return render(request, 'dashboard/index.html', {
        'metrics': metrics,
        'chart_data_json': json.dumps(charts),
        'recent_sales': recent_sales,
        'recent_products': recent_products,
    })


dashboard_index = index


def dashboard_metrics_api(request):
    """API endpoint to refresh dashboard metrics asynchronously."""
    metrics = get_dashboard_metrics()
    # Convert Decimals to float or str for JSON serialization
    serialized = {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in metrics.items()
    }
    return success_response(serialized, message="Dashboard metrics retrieved successfully.")

