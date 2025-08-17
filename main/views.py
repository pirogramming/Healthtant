# views.py
from django.shortcuts import render
from foods.models import Food
import random

def main_page(request):
    sorted_foods = list(
        Food.objects
        .exclude(image_url__isnull=True)
        .exclude(image_url='')
        .order_by('-nutrition_score')[:300]
    )

    foods = sorted_foods[:10]

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
