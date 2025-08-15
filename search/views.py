from django.shortcuts import render
from common.nutrition_score import NutritionalScore
from foods.models import Food
from django.http import JsonResponse

#to FE: food를 이런 형태의 데이터로 넘겨줄겁니다! 더 필요한 값 있거나 문제있는 값 있으면 바로 연락해주세요!!
def food_to_dict(food):
    ret = {
        "food_id": getattr(food, "food_id"),
        "product_image_url": getattr(food, "product_image_url", "") or "",
        "food_name": getattr(food, "food_name", "") or "",
        "food_category": getattr(food, "food_category", "") or "",
        "calorie": getattr(food, "calorie", 0) or 0,
        "moisture": getattr(food, "moisture", 0) or 0,
        "protein": getattr(food, "protein", 0) or 0,
        "fat" : getattr(food, "fat", 0) or 0,
        "carbohydrate": getattr(food, "carbohydrate", 0) or 0,
        "sugar" : getattr(food, "sugar", 0) or 0,
        "dietary_fiber": getattr(food, "dietary_fiber", 0) or 0,
        "salt": getattr(food, "salt", 0) or 0,
        "cholesterol": getattr(food, "cholesterol", 0) or 0,
        "saturated_fatty_acids": getattr(food, "saturated_fatty_acids", 0) or 0,
        "trans_fatty_acids": getattr(food, "trans_fatty_acids", 0) or 0,
        "serving_size": getattr(food, "serving_size", 0) or 0,
        "weight": getattr(food, "weight", 0) or 0,
        "company_name": getattr(food, "company_name", "") or ""
    }
    return ret

#일반 검색 메인 페이지 렌더링 뷰
#영양 점수가 높은 음식들(기본으로 띄울 음식들)을 추려서 프론트로 전달합니다!
def search_page(request):
    
    foods = list(Food.objects.all()) #DB 전체 음식 리스트
    
    # 영양 점수가 높은 식품이 앞에 오도록 정렬
    foods_sorted = sorted(
        foods,
        key=lambda food: NutritionalScore(food),
        reverse=True
    )

    # 반환할 값 구성하는 부분
    context = {"foods":[]}
    for food in foods:
        context["foods"].append(food_to_dict(food))
    
    return render(request, "search/search_page.html", context)


#실제 검색 기능을 구현한 뷰
#Ajax 쓰라는 의미에서 JsonResponse로 드렸습니다 ^^
def normal_search(request):

    keyword = request.GET.get('keyword')
    
    filtered_list = Food.objects.filter(food_name__icontains=keyword) # keyword를 포함한 음식 1차 필터링
    sorted_list = sorted(filtered_list, key=lambda food: NutritionalScore(food), reverse=True) # NutritionalScore 기준 점수가 높은 음식이 앞에 오도록 정렬

    # 반환 값을 구성하는 부분
    context = {"foods":[]}
    for food in sorted_list:
        context["foods"].append(food_to_dict(food))

    # to FE: AJAX로 검색 결과를 노출해야 하므로 Json 데이터를 반환하게 구현했습니다.
    # to FE: 만약 렌더링 해야 할 페이지가 따로 있다면 얘기해주세요!!
    return JsonResponse(context, json_dumps_params={'ensure_ascii': False})