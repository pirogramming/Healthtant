# views.py
from django.shortcuts import render
from django.db.models import Prefetch
from foods.models import Food, Price

def main_page(request):
    prefetch_prices = Prefetch(
        'prices',
        queryset=Price.objects.order_by('-created_at', '-price_id'),
        to_attr='price_list',
    )

    foods = (
        Food.objects
        .exclude(food_img__isnull=True)
        .exclude(food_img='')
        .prefetch_related(prefetch_prices)
        .order_by('-created_at', '-food_id')[:100]
    )

    return render(request, 'main/main_mainpage.html', {'foods': foods})

def permission_denied_view(request, exception=None):
    """403 에러 페이지 뷰"""
    return render(request, 'errors/errors_403.html', status=403)

def not_found_view(request, exception=None):
    """404 에러 페이지 뷰"""
    return render(request, 'errors/errors_404.html', status=404)

def bad_request_view(request, exception=None):
    """400 에러 페이지 뷰"""
    return render(request, 'errors/errors_400.html', status=400)

def server_error_view(request, exception=None):
    """500 에러 페이지 뷰"""
    return render(request, 'errors/errors_500.html', status=500)
