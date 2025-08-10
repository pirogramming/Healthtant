from django.urls import path
from .views import product_detail, toggle_favorite

urlpatterns = [
    path('<uuid:product_id>/', product_detail, name='product-detail'),
    path('<uuid:product_id>/like/', toggle_favorite, name='product-like'),
]