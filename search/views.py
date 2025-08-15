from django.shortcuts import render
from common.nutrition_score import NutritionalScore, letterGrade
from foods.models import Food
from diets.models import Diet
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Case, When
from datetime import datetime, timedelta, date
from analysis.views import make_evaluation, calculate_recommendation, get_real_nutrient
import functools
import uuid

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

#추천 제품 페이지 렌더링 뷰
#영양 점수가 높은 음식들을 랜덤으로 선택해서 프론트로 전달합니다!
def search_before(request):
    import random
    
    foods = list(Food.objects.all()) #DB 전체 음식 리스트
    
    # 영양 점수가 높은 식품이 앞에 오도록 정렬
    foods_sorted = sorted(
        foods,
        key=lambda food: NutritionalScore(food),
        reverse=True
    )
    
    # 상위 50개 제품 중에서 랜덤으로 10개 선택
    top_foods = foods_sorted[:50]
    random_foods = random.sample(top_foods, min(10, len(top_foods)))

    # 반환할 값 구성하는 부분
    context = {"foods":[]}
    for food in random_foods:
        context["foods"].append(food_to_dict(food))
    
    return render(request, "search/search_before.html", context)


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

# 고급 검색 기능 뷰
# 처음에 고급 검색에서 키워드를 입력하여 검색하면 실행할 뷰입니다.
# 정렬과 범위 설정은 검색 결과가 존재하는 상태에서 실행할 함수로 따로 나눴습니다.
@login_required
def search_start(request):
    keyword = request.GET.get('keyword','').strip() #검색 키워드
    qs = Food.objects.all() # DB에 있는 모든 Food를 모두 가져옴
    # 키워드가 있다면 필터링까지 진행
    if keyword:
        qs = qs.filter(Q(food_name__icontains=keyword))

    # 원본 결과 ID 목록을 캐시에 저장해 둠 (추후 정렬과 범위 변경을 위함)
    ids = list(qs.values_list('food_id', flat=True))
    token = str(uuid.uuid4())
    cache.set(f'search:{request.user.id}:{token}', ids, timeout=600)  # 10분 뒤면 캐시 만료됨
    
    # 첫 페이지(또는 요청된 페이지) 반환
    page_number = int(request.GET.get('page', 1))
    paginator = Paginator(qs, 30)  # 페이지당 30개
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    data = {
        "search_token": token, #검색 결과를 다시 불러오기 위한 토큰
        "keyword": keyword, #유저가 검색한 키워드
        "page": page_obj.number, #현재 페이지
        "total_pages": paginator.num_pages, #전체 페이지 수
        "total": paginator.count,
        "foods": [food_to_dict(f) for f in page_obj.object_list], #검색 결과 나올 음식들 데이터
    }

    return JsonResponse(data)


# 쿼리로 주어진 범위를 받은 뒤 
def _parse_ranges(request):
    def f(name):
        try: return float(request.GET.get(name))
        except (TypeError, ValueError): return None
    return {
        'calorie':      (f('calorie_min'),      f('calorie_max')),
        'carbohydrate': (f('carbohydrate_min'), f('carbohydrate_max')),
        'protein':      (f('protein_min'),      f('protein_max')),
        'fat':          (f('fat_min'),          f('fat_max')),
        'salt':         (f('salt_min'),         f('salt_max')),
        'sugar':      (f('sugar_min'),        f('sugar_max')),
    }

ORDER_MAP = {
    "단백질이 많은": "-protein",
    "당이 적은": "sugar",
    "포화지방이 적은": "saturated_fatty_acids",
    "나트륨이 적은": "salt",
    "열량이 많은": "-calorie",
    "열량이 적은": "calorie"
}

# 검색 결과에서 정렬/범위만 변경하는 함수
# 이전에 최초 검색에서 받았던 토큰을 넘겨줘야 합니다!
@login_required
def search_refine(request):
    token = request.GET.get('token')
    order = (request.GET.get('order') or '').strip()
    page  = int(request.GET.get('page', 1))
    size  = int(request.GET.get('size', 30))
    keyword = (request.GET.get('keyword') or '').strip()
    ranges = _parse_ranges(request)

    # 1) 토큰이 있으면 캐시에서 베이스 ID 목록 복구
    ids = cache.get(f'search:{request.user.id}:{token}') if token else None

    # 2) 없으면 새로 초기화(키워드가 없어도 전체셋으로 가능)
    if ids is None:
        base_qs = Food.objects.all()
        if keyword:
            base_qs = base_qs.filter(Q(food_name__icontains=keyword))

        # MAX_BASE 를 설정해서 과하게 많은 값이 출력되지 않게 방어
        MAX_BASE = 20000
        count = base_qs.count()
        if count > MAX_BASE:
            return JsonResponse({"error": f"검색 범위가 너무 큽니다({count}건). 키워드나 범위를 먼저 좁혀주세요."}, status=400)
        ids = list(base_qs.values_list('food_id', flat=True))
        token = str(uuid.uuid4())
        cache.set(f'search:{request.user.id}:{token}', ids, 600)  # 10분 지나면 캐시 만료

    # 3) 베이스셋에 범위/정렬 적용
    qs = Food.objects.filter(food_id__in=ids)

    # 설정한 범위에 맞는 음식만 필터링
    for field, (mn, mx) in ranges.items():
        print(field, mn, mx)
        if mn is not None and mx is not None and mn > mx:
            mn, mx = mx, mn
        if mn is not None:
            qs = qs.filter(**{f'{field}__gte': mn})
        if mx is not None:
            qs = qs.filter(**{f'{field}__lte': mx})

    qs = qs.order_by(ORDER_MAP[order]) # 정렬 적용

    # 페이지네이션 및 반환
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)
    data = {
        "search_token": token,
        "keyword": keyword,
        "order": order,
        "page": page_obj.number,
        "size": size,
        "total_pages": paginator.num_pages,
        "total": paginator.count,
        "foods": [food_to_dict(f) for f in page_obj.object_list],
    }
    return JsonResponse(data)
