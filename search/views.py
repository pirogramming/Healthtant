from django.shortcuts import render
from common.nutrition_score import NutritionalScore, letterGrade
from foods.models import Food, FavoriteFood
from diets.models import Diet
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Case, When
from datetime import datetime, timedelta, date
from analysis.views import make_evaluation, calculate_recommendation, get_real_nutrient
import functools, random, uuid

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

def foods_to_dict(foods, user):
    favorite_ids = set()
    if user and user.is_authenticated:
        favorite_ids = set(
            FavoriteFood.objects.filter(user=user, food__in=foods)
            .values_list("food_id", flat=True)
        )
    return [
        food_to_dict(food, user=user, favorite_ids=favorite_ids)
        for food in foods
    ]
        
#to FE: food를 이런 형태의 데이터로 넘겨줄겁니다! 더 필요한 값 있거나 문제있는 값 있으면 바로 연락해주세요!!
def food_to_dict(food, user=None, favorite_ids=None):
    is_favorite = False
    if user and user.is_authenticated:
        if favorite_ids is not None:
            is_favorite = food.food_id in favorite_ids
        else:
            is_favorite = FavoriteFood.objects.filter(user=user, food=food).exists()  
            
    ret = {
        "food_id": safe_str(getattr(food, "food_id", "")),
        "food_img": safe_str(getattr(food, "image_url", "") or getattr(food, "food_img", "") or ""),
        "food_name": safe_str(getattr(food, "food_name", "") or ""),
        "food_category": safe_str(getattr(food, "food_category", "") or ""),
        "calorie": safe_float(getattr(food, "calorie", 0)),
        "moisture": safe_float(getattr(food, "moisture", 0)),
        "protein": safe_float(getattr(food, "protein", 0)),
        "fat": safe_float(getattr(food, "fat", 0)),
        "carbohydrate": safe_float(getattr(food, "carbohydrate", 0)),
        "sugar": safe_float(getattr(food, "sugar", 0)),
        "dietary_fiber": safe_float(getattr(food, "dietary_fiber", 0)),
        "salt": safe_float(getattr(food, "salt", 0)),
        "cholesterol": safe_float(getattr(food, "cholesterol", 0)),
        "saturated_fatty_acids": safe_float(getattr(food, "saturated_fatty_acids", 0)),
        "trans_fatty_acids": safe_float(getattr(food, "trans_fatty_acids", 0)),
        "serving_size": safe_float(getattr(food, "serving_size", 0)),
        "weight": safe_float(getattr(food, "weight", 0)),
        "company_name": safe_str(getattr(food, "shop_name", "") or getattr(food, "company_name", "") or ""),
        "score": safe_float(getattr(food, "nutrition_score", 0)),
        "letter_grade": safe_str(getattr(food, "nutri_score_grade", "") or letterGrade(food) or ""),
        "nutri_score_grade": safe_str(getattr(food, "nutri_score_grade", "") or letterGrade(food) or ""),
        "is_favorite": is_favorite,
    }
    return ret

#일반 검색 메인 페이지 렌더링 뷰
#검색어가 있을 때만 검색 결과를 보여줍니다
def search_page(request):
    keyword = request.GET.get('keyword', '').strip()
    
    if not keyword:
        # 검색어가 없으면 빈 결과 반환
        context = {"foods": [], "keyword": ""}
        return render(request, "search/search_page.html", context)
    
    # 검색어가 있으면 검색 결과 반환 (서버 사이드 렌더링용)
    filtered_list = Food.objects.filter(food_name__icontains=keyword).order_by("-nutrition_score")
    
    # 반환할 값 구성하는 부분
    context = {"foods": foods_to_dict(filtered_list, request.user), "keyword": keyword}
    
    return render(request, "search/search_page.html", context)

#실제 검색 기능을 구현한 뷰
#Ajax 쓰라는 의미에서 JsonResponse로 드렸습니다 ^^
def normal_search(request):
    keyword = request.GET.get('keyword')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 30))
    
    if not keyword:
        return JsonResponse({"foods": []}, json_dumps_params={'ensure_ascii': False})
    
    # 검색어가 있으면 필터 + DB에서 바로 점수 내림차순 정렬
    filtered_list = Food.objects.filter(food_name__icontains=keyword).order_by("-nutrition_score")
    
    # 페이지네이션 적용
    start_index = (page - 1) * limit
    end_index = start_index + limit
    paginated_list = filtered_list[start_index:end_index]

    # 반환 값을 구성하는 부분
    context = {"foods": foods_to_dict(paginated_list, request.user)}

    # to FE: AJAX로 검색 결과를 노출해야 하므로 Json 데이터를 반환하게 구현했습니다.
    # to FE: 만약 렌더링 해야 할 페이지가 따로 있다면 얘기해주세요!!
    return JsonResponse(context, json_dumps_params={'ensure_ascii': False})

#추천 제품 페이지 렌더링 뷰
#영양 점수가 높은 음식들을 랜덤으로 선택해서 프론트로 전달합니다!
def search_before(request):
    
    top_foods = list(Food.objects.order_by('-nutrition_score')[:50]) # 영양 점수가 높은 식품이 앞에 오도록 정렬

    random_foods = random.sample(top_foods, min(10, len(top_foods)))

    # 반환할 값 구성하는 부분
    context = {"foods":foods_to_dict(random_foods, request.user)}
    
    return render(request, "search/search_before.html", context)


#실제 검색 기능을 구현한 뷰
#Ajax 쓰라는 의미에서 JsonResponse로 드렸습니다 ^^
def normal_search(request):

    keyword = request.GET.get('keyword')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 30))
    
    filtered_list = Food.objects.filter(food_name__icontains=keyword) # keyword를 포함한 음식 1차 필터링
    sorted_list = sorted(filtered_list, key=lambda food: NutritionalScore(food), reverse=True) # NutritionalScore 기준 점수가 높은 음식이 앞에 오도록 정렬

    # 페이지네이션 적용
    start_index = (page - 1) * limit
    end_index = start_index + limit
    paginated_list = sorted_list[start_index:end_index]

    # 반환 값을 구성하는 부분
    context = {"foods":foods_to_dict(paginated_list, request.user)}

    # to FE: AJAX로 검색 결과를 노출해야 하므로 Json 데이터를 반환하게 구현했습니다.
    # to FE: 만약 렌더링 해야 할 페이지가 따로 있다면 얘기해주세요!!
    return JsonResponse(context, json_dumps_params={'ensure_ascii': False})


#상세 검색 렌더링 뷰
#사용자가 필요로 할 법한 제품을 우선으로 출력합니다.
@login_required
def advanced_search_page(request):
    # AJAX 요청 처리
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 4))
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

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
            "calorie",
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

        def append_order(order_list, evaluation, field):
            level = evaluation["level"]
            if level in ("부족", "매우 부족"):
                order_list.append(f'-{field}')
            elif level in ("과다", "매우 과다"):
                order_list.append(field)

        ORDER_BY = ['-nutrition_score']
        append_order(ORDER_BY, calorie_evaluation, 'calorie')
        append_order(ORDER_BY, carbohydrate_evaluation, 'carbohydrate')
        append_order(ORDER_BY, protein_evaluation, 'protein')
        append_order(ORDER_BY, fat_evaluation, 'fat')
        append_order(ORDER_BY, salt_evaluation, 'salt')

        # 페이지네이션 적용
        start = (page - 1) * limit
        end = start + limit
        foods_sorted = Food.objects.order_by(*ORDER_BY)[start:end]

        foods_data = []
        for food in foods_sorted:
            foods_data.append(food_to_dict(food))
        
        return JsonResponse({
            'foods': foods_data,
            'page': page,
            'has_more': foods_sorted.count() == limit
        })

    # 일반 HTML 요청 처리 (기존 로직)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

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
        "calorie",
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

    def append_order(order_list, evaluation, field):
        level = evaluation["level"]
        if level in ("부족", "매우 부족"):
            order_list.append(f'-{field}')
        elif level in ("과다", "매우 과다"):
            order_list.append(field)

    ORDER_BY = ['-nutrition_score']
    append_order(ORDER_BY, calorie_evaluation, 'calorie')
    append_order(ORDER_BY, carbohydrate_evaluation, 'carbohydrate')
    append_order(ORDER_BY, protein_evaluation, 'protein')
    append_order(ORDER_BY, fat_evaluation, 'fat')
    append_order(ORDER_BY, salt_evaluation, 'salt')

    foods_sorted = Food.objects.order_by(*ORDER_BY)[:10]

    # 반환할 값 구성하는 부분
    context = {"foods":foods_to_dict(foods_sorted, request.user)}
    
    return render(request, "search/advanced_search_page.html", context)

# 고급 검색 기능 뷰
# 처음에 고급 검색에서 키워드를 입력하여 검색하면 실행할 뷰입니다.
# 정렬과 범위 설정은 검색 결과가 존재하는 상태에서 실행할 함수로 따로 나눴습니다.
@login_required
def search_start(request):
    keyword = request.GET.get('keyword','').strip() #검색 키워드
    #내가 여기를 수정했는데 이게 맞는지 틀린지 확인 부탁해요!!!
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' :
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
        limit = int(request.GET.get('limit', 30))
        paginator = Paginator(qs, limit)  # 페이지당 limit개
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
            "foods": foods_to_dict(page_obj.object_list, request.user), #검색 결과 나올 음식들 데이터
        }

        return JsonResponse(data)

    context = {
        'keyword': keyword,
    }
    return render(request, 'search/advanced_result.html', context)




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
        "foods": foods_to_dict(page_obj.object_list, request.user),
    }
    return JsonResponse(data)


