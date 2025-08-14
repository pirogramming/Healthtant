from django.urls import path
from .views import product_detail, toggle_favorite

app_name = "products"

urlpatterns = [
    path("<str:product_id>/", product_detail, name="product-detail"),
    path("<str:product_id>/like/", toggle_favorite, name="product-like"),
]