from django.shortcuts import render
from common.nutrition_score import NutritionalScore
from foods.models import Food
from django.http import JsonResponse

#일반 검색 메인 페이지 렌더링 뷰
def search_page(request):
    
    foods = list(Food.objects.all())
    
    foods_sorted = sorted(
        foods,
        key=lambda food: NutritionalScore(food),
        reverse=True
    )

    context = {foods_sorted}

    return render(request, "search_page.html", context)


#일반 검색 뷰
#Ajax 쓰라는 의미에서 JsonResponse로 드렸습니다
def normal_search(request):
    keyword = request.GET.get('keyword')
    
    filtered_list = Food.objects.filter(food_name__icontains=keyword)
    sorted_list = sorted(filtered_list, key=lambda food: NutritionalScore(food), reverse=True)

    context = {sorted_list}

    return JsonResponse(context, json_dumps_params={'ensure_ascii': False})