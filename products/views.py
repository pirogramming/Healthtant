from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from foods.models import Food, FavoriteFood


def _product_dict(food, is_favorite: bool):
    return {
        "food_id": str(food.pk),
        "food_img": food.food_img or "",
        "food_name": food.food_name,
        "calorie": food.calorie,
        "protein": food.protein,
        "fat": food.fat,
        "carbohydrate": food.carbohydrate,
        "sodium": food.salt,
        "nutrition_score": None,
        "is_favorite": is_favorite,
    }


@require_GET
def product_detail(request, product_id):
    food = get_object_or_404(Food, pk=product_id)
    is_fav = (
        request.user.is_authenticated
        and FavoriteFood.objects.filter(user_id=request.user.id, food=food).exists()
    )

    data = _product_dict(food, is_fav)

    # JSON이 필요하면 명시적으로 응답
    wants_json = (
        request.GET.get("format") == "json"
        or "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json:
        return JsonResponse(data)

    # 기본은 SSR 렌더링
    return render(request, "products/products_detail.html", {"product": data})


@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, product_id):
    """
    POST /products/<uuid>/like/
    """
    food = get_object_or_404(Food, pk=product_id)
    fav_qs = FavoriteFood.objects.filter(user_id=request.user.id, food=food)

    if fav_qs.exists():
        fav_qs.delete()
        return JsonResponse({"is_favorite": False})

    FavoriteFood.objects.create(user_id=request.user.id, food=food)
    return JsonResponse({"is_favorite": True})