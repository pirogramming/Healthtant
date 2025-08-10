
# products/views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required

from foods.models import Food, FavoriteFood


def _product_dict(food, is_favorite: bool):
    """
    DB 스키마 ↔ 응답 JSON 맵핑
    - sodium ← Food.salt (DB 컬럼명이 salt)
    - nutrition_score: 없으면 일단 None (필요시 계산 로직 넣자)
    """
    return {
        "food_id": str(food.pk),    
        "food_img": food.food_img or "",      # null 방지
        "food_name": food.food_name,
        "calorie": food.calorie,
        "protein": food.protein,
        "fat": food.fat,
        "carbohydrate": food.carbohydrate,
        "sodium": food.salt,                 
        "nutrition_score": None,              # TODO: 필요시 계산/저장
        "is_favorite": is_favorite,
    }


@require_GET
def product_detail(request, product_id):
    """
    GET /products/<uuid:product_id>/
    - Food 1건 + 즐겨찾기 여부
    """
    food = get_object_or_404(Food, pk=product_id)

    # 즐겨찾기 여부
    is_fav = (
        request.user.is_authenticated
        and FavoriteFood.objects.filter(user_id=request.user.id, food=food).exists()
    )

    return JsonResponse(_product_dict(food, is_fav))


@login_required
@require_http_methods(["PATCH"])
def toggle_favorite(request, product_id):
    """
    PATCH /products/<uuid:product_id>/like/
    - Favorite_Food 토글 (user_id, food_id)
    """
    food = get_object_or_404(Food, pk=product_id)
    fav_qs = FavoriteFood.objects.filter(user_id=request.user.id, food=food)

    if fav_qs.exists():
        fav_qs.delete()
        return JsonResponse({"is_favorite": False})

    FavoriteFood.objects.create(user_id=request.user.id, food=food)
    return JsonResponse({"is_favorite": True})
