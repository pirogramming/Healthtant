from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from common import nutrition_score

from foods.models import Food, FavoriteFood

# bytes 타입을 문자열로 변환하는 헬퍼 함수
def safe_str(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    elif value is None:
        return ""
    else:
        return str(value)

# 안전한 숫자 변환 함수
def safe_float(value, default=0.0):
    if isinstance(value, bytes):
        try:
            return float(value.decode('utf-8', errors='ignore'))
        except:
            return default
    elif value is None:
        return default
    else:
        try:
            return float(value)
        except:
            return default
        
# 안전한 숫자 변환 함수
def safe_int(value, default=0):
    if isinstance(value, bytes):
        try:
            return int(value.decode('utf-8', errors='ignore'))
        except:
            return default
    elif value is None:
        return default
    else:
        try:
            return int(value)
        except:
            return default

def _product_dict(food, is_favorite: bool):
    return {
        "food_id": str(food.pk),
        "food_img": safe_str(food.image_url) or safe_str(food.food_img) or "",
        "food_name": safe_str(food.food_name),
        "calorie": safe_float(food.calorie),
        "moisture": safe_float(food.moisture),
        "protein": safe_float(food.protein),
        "fat": safe_float(food.fat),
        "carbohydrate": safe_float(food.carbohydrate),
        "sugar": safe_float(food.sugar),
        "dietary_fiber": safe_float(food.dietary_fiber),
        "calcium": safe_float(food.calcium),
        "iron_content": safe_float(food.iron_content),
        "phosphorus": safe_float(food.phosphorus),
        "potassium": safe_float(food.potassium),
        "sodium": safe_float(food.salt),
        "VitaminA": safe_float(food.VitaminA),
        "VitaminB": safe_float(food.VitaminB),
        "VitaminC": safe_float(food.VitaminC),
        "VitaminD": safe_float(food.VitaminD),
        "VitaminE": safe_float(food.VitaminE),
        "cholesterol": safe_float(food.cholesterol),
        "saturated_fatty_acids": safe_float(food.saturated_fatty_acids),
        "trans_fatty_acids": safe_float(food.trans_fatty_acids),
        "nutritional_value_standard_amount": safe_int(food.nutritional_value_standard_amount),
        "weight": safe_float(food.weight),
        "company_name": safe_str(food.mallName) or safe_str(food.company_name),
        "nutrition_score": safe_float(food.nutrition_score),
        "nutri_score_grade": safe_str(food.nutri_score_grade),
        "lprice": safe_int(food.lprice),
        "shop_name": safe_str(food.mallName),
        "shop_url": safe_str(food.shop_url),
        "sugar_level": None,
        "saturated_fatty_acids_level": None,
        "salt_level": None,
        "protein_level": None,
        "is_favorite": is_favorite,
    }

@require_GET
def product_detail(request, food_id):
    food = get_object_or_404(Food, pk=food_id)
    is_fav = (
        request.user.is_authenticated
        and FavoriteFood.objects.filter(user_id=request.user.id, food=food).exists()
    )

    data = _product_dict(food, is_fav)

    data["nutrition_score"] = safe_float(food.nutrition_score) or nutrition_score.NutritionalScore(food) # 0 ~ 26점 반환
    data["nutri_score_grade"] = safe_float(food.nutri_score_grade) or nutrition_score.letterGrade(food) #A, B, C, D, E
    
    data["sugar_level"] = nutrition_score.get_level("sugar", food) # ex) {"level": "낮음", "class": "GOOD"}
    data["saturated_fatty_acids_level"]= nutrition_score.get_level("saturated_fatty_acids", food) # ex) {"level": "낮음", "class": "GOOD"}
    data["salt_level"] = nutrition_score.get_level("salt", food) # ex) {"level": "낮음", "class": "GOOD"}
    data["protein_level"] = nutrition_score.get_level("protein", food) # ex) {"level": "낮음", "class": "GOOD"}

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


@login_required(login_url='/accounts/login/')
@require_http_methods(["POST"])
def toggle_favorite(request, food_id):
    """
    POST /products/<food_id>/like/
    """
    food = get_object_or_404(Food, pk=food_id)
    fav_qs = FavoriteFood.objects.filter(user_id=request.user.id, food=food)

    if fav_qs.exists():
        fav_qs.delete()
        return JsonResponse({"is_favorite": False})

    FavoriteFood.objects.create(user_id=request.user.id, food=food)
    return JsonResponse({"is_favorite": True})
