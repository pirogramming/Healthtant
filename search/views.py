from django.shortcuts import render
from common.nutrition_score import NutritionalScore, letterGrade
from foods.models import Food
from diets.models import Diet
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, date
from analysis.views import make_evaluation, calculate_recommendation, get_real_nutrient
import functools

#to FE: food를 이런 형태의 데이터로 넘겨줄겁니다! 더 필요한 값 있거나 문제있는 값 있으면 바로 연락해주세요!!
def food_to_dict(food):
    ret = {
        "food_id": getattr(food, "food_id"),
        "food_img": getattr(food, "food_img", "") or "",
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
        "company_name": getattr(food, "company_name", "") or "",
        "score": NutritionalScore(food),
        "letter_grade": letterGrade(food)
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
    for food in foods_sorted:
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


#상세 검색 렌더링 뷰
#사용자가 필요로 할 법한 제품을 우선으로 출력합니다.
@login_required
def advanced_search_page(request):

    end_date = date.today()                # 오늘 날짜
    start_date = end_date - timedelta(days=30)  # 30일 전 날짜

    diet_query_set = Diet.objects.select_related('food').filter(
        user=request.user,
        date__range=(start_date, end_date)
    )

    nutrients_avg = {'calorie': 0.00, 'carbohydrate': 0.00, 'protein': 0.00, 'fat':0.00, 'salt': 0.00}

    for diet in diet_query_set:
        food = diet.food
        nutrients_avg['calorie'] += get_real_nutrient(food, "calorie")
        nutrients_avg['carbohydrate'] += get_real_nutrient(food, "carbohydrate")
        nutrients_avg['protein'] += get_real_nutrient(food, "protein")
        nutrients_avg['fat'] += get_real_nutrient(food, "fat")
        nutrients_avg['salt'] += get_real_nutrient(food, "salt")

    for nutrient, sum in nutrients_avg.items():
        nutrients_avg[nutrient] = round(sum/30, 2)

    recommendation = calculate_recommendation(request.user)

    calorie_evaluation = make_evaluation(
        "carbohydrate",
        nutrients_avg['calorie'],
        recommendation['calorie']['min'],
        recommendation['calorie']['max'],
        recommendation['calorie']['essential']
    )
    carbohydrate_evaluation = make_evaluation(
        "carbohydrate",
        nutrients_avg['carbohydrate'], 
        recommendation['carbohydrate']['min'],
        recommendation['carbohydrate']['max'],
        recommendation['carbohydrate']['essential']
    )
    protein_evaluation = make_evaluation(
        "protein",
        nutrients_avg['protein'], 
        recommendation['protein']['min'],
        recommendation['protein']['max'],
        recommendation['protein']['essential']
    )
    fat_evaluation = make_evaluation(
        "fat",
        nutrients_avg['fat'], 
        recommendation['fat']['min'],
        recommendation['fat']['max']
    )
    salt_evaluation = make_evaluation(
        "salt",
        nutrients_avg['salt'], 
        recommendation['salt']['min'],
        recommendation['salt']['max'],
        recommendation['salt']['essential']
    )

    # food1과 food2를 영양점수로 먼저 비교하고, 만약 영양점수가 같다면 사용자가 필요로 하는 영양소를 다량 함유한 식품이 앞에 오도록 정렬하는 기준을 제공하는 comparator
    def comparator(food1,food2):
        #영양 점수 2개 먼저 계산
        score1 = NutritionalScore(food1)
        score2 = NutritionalScore(food2)

        # 영양 점수가 다르다면 점수만을 가지고 정렬하도록 반환
        if score1 != score2: return score1 - score2

        # food1의 영양소 정보
        calorie1 = getattr(food1, "calorie", 0) or 0
        carbohydrate1 = getattr(food1, "carbohydrate", 0) or 0
        protein1 = getattr(food1, "protein", 0) or 0
        fat1 = getattr(food1, "fat", 0) or 0
        salt1 = getattr(food1, "salt", 0) or 0

        # food2의 영양소 정보
        calorie2 = getattr(food2, "calorie", 0) or 0
        carbohydrate2 = getattr(food2, "carbohydrate", 0) or 0
        protein2 = getattr(food2, "protein", 0) or 0
        fat2 = getattr(food2, "fat", 0) or 0
        salt2 = getattr(food2, "salt", 0) or 0

        # 칼로리 비교 (섭취가 부족할 경우 많이 함유한 식품이 우세, 그렇지 않은 경우 적게 함유한 식품이 우세)
        calorie_state = calorie_evaluation["level"]
        if calorie_state == "부족" or calorie_state == "매우 부족":
            if calorie1 > calorie2: score1 += 1
            elif calorie1 < calorie2: score2 += 1
        elif calorie_state == "과다" or calorie_state == "매우 과다":
            if calorie1 > calorie2: score2 += 1
            elif calorie1 < calorie2: score1 += 1

        # 탄수화물 비교 (섭취가 부족할 경우 많이 함유한 식품이 우세, 그렇지 않은 경우 적게 함유한 식품이 우세)
        carbohydrate_state = carbohydrate_evaluation["level"]
        if carbohydrate_state == "부족" or carbohydrate_state == "매우 부족":
            if carbohydrate1 > carbohydrate2: score1 += 1
            elif carbohydrate1 < carbohydrate2: score2 += 1
        elif carbohydrate_state == "과다" or carbohydrate_state == "매우 과다":
            if carbohydrate1 > carbohydrate2: score2 += 1
            elif carbohydrate1 < carbohydrate2: score1 += 1

        # 단백질 비교 (섭취가 부족할 경우 많이 함유한 식품이 우세, 그렇지 않은 경우 적게 함유한 식품이 우세)
        protein_state = protein_evaluation["level"]
        if protein_state == "부족" or protein_state == "매우 부족":
            if protein1 > protein2: score1 += 1
            elif protein1 < protein2: score2 += 1
        elif protein_state == "과다" or protein_state == "매우 과다":
            if protein1 > protein2: score2 += 1
            elif protein1 < protein2: score1 += 1

        # 지방 비교 (섭취가 부족할 경우 많이 함유한 식품이 우세, 그렇지 않은 경우 적게 함유한 식품이 우세)
        fat_state = fat_evaluation["level"]
        if fat_state == "부족" or fat_state == "매우 부족":
            if fat1 > fat2: score1 += 1
            elif fat1 < fat2: score2 += 1
        elif fat_state == "과다" or fat_state == "매우 과다":
            if fat1 > fat2: score2 += 1
            elif fat1 < fat2: score1 += 1

        # 나트륨 비교 (섭취가 부족할 경우 많이 함유한 식품이 우세, 그렇지 않은 경우 적게 함유한 식품이 우세)
        salt_state = salt_evaluation["level"]
        if salt_state == "부족" or salt_state == "매우 부족":
            if salt1 > salt2: score1 += 1
            elif salt1 < salt2: score2 += 1
        elif salt_state == "과다" or salt_state == "매우 과다":
            if salt1 > salt2: score2 += 1
            elif salt1 < salt2: score1 += 1

        return score1 - score2
    
    foods = list(Food.objects.all()) #DB 전체 음식 리스트
    
    # 영양 점수가 높은 식품이 앞에 오도록 정렬
    foods_sorted = sorted(
        foods,
        key=functools.cmp_to_key(comparator),
        reverse=True
    )

    # 반환할 값 구성하는 부분
    context = {"foods":[]}
    for food in foods_sorted:
        context["foods"].append(food_to_dict(food))
    
    return render(request, "search/advanced_search_page.html", context)