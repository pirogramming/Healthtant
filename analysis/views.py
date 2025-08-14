from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from diets.models import Diet
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Sum, F, Count, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest
from statistics import pstdev

# 임시 날짜 선택 페이지 뷰 (확인용)
def analysis_date(request):
    # 로그인 상태 확인 - 로그인 안 되어도 페이지는 렌더링
    return render(request, 'analysis/analysis_date.html')

#user의 각 영양소별 필수섭취량, 적정량 범위를 구하는 메소드
def calculate_recommendation(user):
    gender = user.profile.user_gender
    age = user.profile.user_age

    #나이가 제대로 입력되지 않은 경우 기본값 설정
    if age == None:
        age = 20
    elif age <= 0:
        age = 1
    elif age >= 150:
        age = 150

    #성별이 OTHER 혹은 그 외의 이상한 값인 경우 남자로 기본 설정
    if not (gender == "M" or gender == "F"):
        gender = "M"

    ret = {
        'calorie' : {
            'min': 0, #user의 적정 에너지 min 값
            'max': 0, #user의 적정 에너지 max 값
            'essential': 0 #user의 에너지 필수섭취량
        },
        'carbohydrate': {
            'min': 0, #user의 적정 탄수화물 min 값
            'max': 0, #user의 적정 탄수화물 max 값
            'essential': 0 #user의 탄수화물 필수섭취량
        },
        'protein': {
            'min': 0, #user의 적정 단백질 min 값
            'max': 0, #user의 적정 단백질 max 값
            'essential': 0 #user의 단백질 필수섭취량
        },
        'fat': {
            'min': 0, #user의 적정 지방 min 값
            'max': 0 #user의 적정 지방 max 값
        },
        'salt': {
            'min': 0, #user의 적정 나트륨 min 값
            'max': 0, #user의 적정 나트륨 max 값
            'essential': 0 #user의 나트륨 필수섭취량
        }
    }

    age_interval = [(1,2), (3,5), (6,8), (9,11), (12,14), (15,18), (19,29), (30,49), (50,64), (65,74), (75,150)]
    for i in range(len(age_interval)):
        start, end = age_interval[i]
        if start <= age <= end:
            idx = i
            break
    
    # 에너지 필요추정량 표 (kcal)
    eer_table = [(900, 900), (1400, 1400), (1700, 1500), (2000, 1800), (2500, 2100), (2700, 2000), (2600, 2000), (2600, 2000), (2400, 1900), (2200, 1800), (2000, 1600)]
    # 단백질 권장섭취량 (g)
    protein_table = [(15, 15), (20, 20), (30, 25), (40, 35), (55, 45), (60, 50), (60, 50), (60, 50), (60, 50), (60, 50), (60, 50)]
    # 나트륨 충분섭취량 (mg)
    min_salt_table = [810, 1000, 1200, 1500, 1500, 1500, 1500, 1500, 1500, 1300, 1100]
    # 나트륨 만성질환 위험감소 섭취량 (mg)
    max_salt_table = [1200, 1600, 1900, 2300, 2300, 2300, 2300, 2300, 2300, 2300, 1700]

    ret['carbohydrate']['essential'] = 130 #필수 탄수화물 양은 성별과 나이에 관계없이 130g으로 동일함
    ret['protein']['essential'] = protein_table[idx][0] if gender == "M" else protein_table[idx][1] #필수 단백질 양
    ret['salt']['essential'] = min_salt_table[idx] #필수 나트륨 양

    recommend_calorie = eer_table[idx][0] if gender == "M" else eer_table[idx][1] #유저의 필요 에너지 추정량 계산

    ret['calorie']['essential'] = recommend_calorie*0.8 #필요 에너지 추정량의 80%를 필수 에너지로 잡음
    ret['calorie']['min'] = recommend_calorie*0.9 #필요 에너지 추정량의 90%를 min으로 잡음
    ret['calorie']['max'] = recommend_calorie*1.1 #필요 에너지 추정량의 110%를 max로 잡음

    ret['carbohydrate']['min'] = recommend_calorie*0.55/4 #2020 한국인 영양소 섭취 기준 '적정 탄수화물 양'
    ret['carbohydrate']['max'] = recommend_calorie*0.65/4 #2020 한국인 영양소 섭취 기준 '적정 탄수화물 양'

    ret['protein']['min'] = recommend_calorie*0.07/4 #2020 한국인 영양소 섭취 기준 '적정 단백질 양'
    ret['protein']['max'] = recommend_calorie*0.2/4 #2020 한국인 영양소 섭취 기준 '적정 단백질 양'

    ret['fat']['min'] = recommend_calorie*0.15/9 #2020 한국인 영양소 섭취 기준 '적정 지방 양'
    ret['fat']['max'] = recommend_calorie*0.3/9 #2020 한국인 영양소 섭취 기준 '적정 지방 양'

    #나트륨은 여성과 남성 기준이 동일함
    ret['salt']['min'] = min_salt_table[idx] #2020 한국인 영양소 섭취 기준 '적정 나트륨 양'
    ret['salt']['max'] = max_salt_table[idx] #2020 한국인 영양소 섭취 기준 '적정 나트륨 양'

    return ret

# 사용자 섭취량(eat)과 적정 섭취 범위(min, max)와 필수섭취량(essential, 기본 0) 을 받아서 현재 섭취가 어느 수준인지 반환
def get_level(eat, min, max, essential=0):
    if eat < essential:
        return "매우 부족"
    elif eat < min:
        return "부족"
    elif eat <= max:
        return "적정"
    elif eat < max + (max-min):
        return "과다"
    else:
        return "매우 과다"

# 영양 섭취 수준을 입력 받아 프론트에서 출력해야 할 색을 반환하는 메소드
def get_color(level):
    if level == "매우 부족" or level == "매우 과다":
        return "#ff3232"
    elif level == "부족" or level == "과다":
        return "#FF9021"
    else:
        return "#56AAB2"

# 영양 섭취 수준을 입력 받아 프론트에서 출력해야 할 메세지를 반환하는 메소드
def get_message(level):
    if level == "매우 부족":
        return "너무 조금 섭취 중입니다. 건강에 심각한 영향을 미칠 수 있어요!!"
    elif level == "부족":
        return "조금 부족하게 섭취 중입니다. 조금만 더 신경 써보는건 어떨까요?"
    elif level == "적정":
        return "아주 적절하게 섭취 중입니다. 이대로 꾸준히 드시면 될 것 같아요!"
    elif level == "과다":
        return "조금 과다하게 섭취 중입니다. 조금만 더 신경 써보는건 어떨까요?"
    else:
        return "너무 과하게 섭취 중입니다. 건강에 심각한 영향을 미칠 수 있어요!!"

# 영양소 이름, 평균섭취량, 최소적정량, 최대적정량, 필수섭취량을 입력 받아서 evaluation을 만들어주는 함수
def make_evaluation(name, avg, min, max, essential=0):
    nutrition_percentage = round(avg/max * 100, 2)
    nutrition_level = get_level(avg, min, max, essential)
    nutrition_color = get_color(nutrition_level)
    nutrition_message = get_message(nutrition_level)

    return {
        "name": name,
        "percentage": nutrition_percentage,
        "level": nutrition_level,
        "color": nutrition_color,
        "message": nutrition_message
    }

# 실제로 food를 1회 섭취했을 때 얻을 수 있는 영양소의 양을 반환하는 함수
def get_real_nutrient(food, nutrient_name):
    serving_size = getattr(food, "serving_size", getattr(food, "weight", 100)) or 100#1회 섭취참고량이 없다면 식품 중량을 기준으로, 식품 중량도 없다면 100g(ml)를 섭취하는 것으로 계산함
    nutritional_value_standard_amount = getattr(food, "nutritional_value_standard_amount", 100) or 100 #model 설계 시 null=False 로 설정이지만... 혹시 모르니 100g(ml)를 기본으로 설정
    nutrient = getattr(food, nutrient_name, 0) or 0 #null인 영양소 필드도 존재함
    weight = getattr(food, "weight") #model 설계시 null=False 로 설정
    
    if nutrient == 0:
        return 0
    
    #1회제공량에 담긴 영양소만큼 반환
    return nutrient / nutritional_value_standard_amount * serving_size

#메인 분석 페이지 뷰
@login_required
def analysis_main(request):
    user = request.user

    try:
        #url에서 쿼리로 주어진 start_date, end_date
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    # 쿼리가 제대로 된 형식으로 주어지지 않았을 경우 예외처리
    except Exception:
        return HttpResponseBadRequest("날짜 형식이 잘못 되었습니다. YYYY-MM-DD 형식을 사용해 주세요.")
    
    # 분석 시작 날짜가 끝 날짜보다 뒤인 경우 예외처리
    if start_date > end_date:
        return HttpResponseBadRequest("분석 시작 날짜는 끝 날짜보다 이전이어야 합니다.")
    
    day_difference = (end_date - start_date).days + 1 #몇 일 차이인지 계산(양 끝 날짜 포함)

    #자주 쓰게 될 쿼리셋을 미리 조회해서 저장해둠
    diet_query_set = Diet.objects.select_related('food').filter(
        user=request.user,
        date__range=(start_date, end_date)
    )

    #--------------------------------------------------여기부터 meal_number 계산-----------------------------------------------------------
    meal_number = day_difference*3 #전체 끼니 수 계산

    #--------------------------------------------------여기부터 product_number 계산-----------------------------------------------------------
    #start_date ~ end_date 동안 먹은 가공식품의 수 계산
    product_number = diet_query_set.count()

    #--------------------------------------------------여기부터 category_status 계산-----------------------------------------------------------

    category_rows = (
        diet_query_set
        .values('food__food_category')
        .annotate(count=Count('diet_id'))
        .order_by('-count')
    )

    # #나중에 프론트랑 상의해서 상위 몇개의 데이터를 전달할 지 정해지면 정렬이랑 슬라이싱도 구현할게요!
    category_status = [
        {'food_category': r['food__food_category'], 'count': r['count']}
        for r in category_rows
    ]

    #--------------------------------------------------여기부터 nutrients_avg 계산-----------------------------------------------------------
    # 섭취한 영양소의 평균을 저장할 딕셔너리
    nutrients_avg = {
        'calorie' : 0,
        'carbohydrate' : 0,
        'protein' : 0,
        'fat' : 0,
        'salt' : 0
    }

    for diet in diet_query_set:
        food = diet.food
        nutrients_avg['calorie'] += get_real_nutrient(food, "calorie")
        nutrients_avg['carbohydrate'] += get_real_nutrient(food, "carbohydrate")
        nutrients_avg['protein'] += get_real_nutrient(food, "protein")
        nutrients_avg['fat'] += get_real_nutrient(food, "fat")
        nutrients_avg['salt'] += get_real_nutrient(food, "salt")

    for nutrient, sum in nutrients_avg.items():
        nutrients_avg[nutrient] = round(sum/day_difference, 2)

    #--------------------------------------------------여기부터 recommend_nutrients 계산-----------------------------------------------------------
    recommend_nutrients = calculate_recommendation(user)

    #--------------------------------------------------여기부터 nutrients_evaluation 계산-----------------------------------------------------------
    nutrient_evaluation = []
    
    #칼로리 계산 시작
    nutrient_evaluation.append(
        make_evaluation(
            "에너지",
            nutrients_avg['calorie'],
            recommend_nutrients['calorie']['min'],
            recommend_nutrients['calorie']['max'],
            recommend_nutrients['calorie']['essential']
        )
    )

    #탄수화물 계산 시작
    nutrient_evaluation.append(
        make_evaluation(
            "탄수화물",
            nutrients_avg['carbohydrate'],
            recommend_nutrients['carbohydrate']['min'],
            recommend_nutrients['carbohydrate']['max'],
            recommend_nutrients['carbohydrate']['essential']
        )
    )

    #단백질 계산 시작
    nutrient_evaluation.append(
        make_evaluation(
            "단백질",
            nutrients_avg['protein'],
            recommend_nutrients['protein']['min'],
            recommend_nutrients['protein']['max'],
            recommend_nutrients['protein']['essential']
        )
    )

    #지방 계산 시작
    nutrient_evaluation.append(
        make_evaluation(
            "지방",
            nutrients_avg['fat'],
            recommend_nutrients['fat']['min'],
            recommend_nutrients['fat']['max']
        )
    )

    #나트륨 계산 시작
    nutrient_evaluation.append(
        make_evaluation(
            "나트륨",
            nutrients_avg['salt'],
            recommend_nutrients['salt']['min'],
            recommend_nutrients['salt']['max'],
            recommend_nutrients['salt']['essential']
        )
    )

    #--------------------------------------------------여기부터 context 반환-----------------------------------------------------------
    context = {
        "meal_number" : meal_number,
        "product_number" : product_number,
        "category_status" : category_status,
        "avg_calorie_per_day" : nutrients_avg['calorie'],
        "avg_carbohydrate_per_day" : nutrients_avg['carbohydrate'],
        "avg_protein_per_day" : nutrients_avg['protein'],
        "avg_fat_per_day" : nutrients_avg['fat'],
        "avg_salt_per_day" : nutrients_avg['salt'],
        "calorie" : recommend_nutrients['calorie'],
        "carbohydrate" : recommend_nutrients['carbohydrate'],
        "protein" : recommend_nutrients['protein'],
        "fat" : recommend_nutrients['fat'],
        "salt" : recommend_nutrients['salt'],
        "nutrients_evaluation": nutrient_evaluation,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
    }

    #나중에 프론트에서 main.html 같은 템플릿 만들고 나면 아래 주석처리 해놓은 render 함수로 바꿔 사용해주세요!
    return render(request, "analysis/analysis_main.html", context)
    # return JsonResponse(context, json_dumps_params={'ensure_ascii': False})


def stdev_summary(stdev):
    if stdev <= 100:
        return "비교적 꾸준히 가공식품을 섭취하고 있어요. 대체로 안정적인 식사 형태를 보이는 것 같습니다!"
    elif stdev <= 300:
        return "가공식품 섭취의 일관성이 부족하며, 이는 영양 불균형 및 소화 불량으로 이어질 수 있습니다."
    else:
        return "일일 섭취량 변동 폭이 큽니다. 특정 날에 폭식하거나 지나치게 제한하는 식습관일 가능성이 있습니다."

# 자세한 식사 분석 뷰
@login_required
def analysis_diet(request):
    try:
        #url에서 쿼리로 주어진 start_date, end_date
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    # 쿼리가 제대로 된 형식으로 주어지지 않았을 경우 예외처리
    except Exception:
        return HttpResponseBadRequest("날짜 형식이 잘못 되었습니다. YYYY-MM-DD 형식을 사용해 주세요.")
    
    # 분석 시작 날짜가 끝 날짜보다 뒤인 경우 예외처리
    if start_date > end_date:
        return HttpResponseBadRequest("분석 시작 날짜는 끝 날짜보다 이전이어야 합니다.")
    
    day_difference = (end_date - start_date).days + 1 #몇 일 차이인지 계산(양 끝 날짜 포함)

    diet_query_set = Diet.objects.select_related('food').filter(
        user=request.user,
        date__range=(start_date, end_date)
    ).order_by('date')

    #--------------------------------------------------여기부터 가공식품과 끼니 관계 계산-----------------------------------------------------------
    meal_number = day_difference*3 #전체 끼니 수 계산
    product_number = diet_query_set.count() #start_date ~ end_date 까지 먹은 가공식품의 수
    meals_with_product_count = diet_query_set.values('date', 'meal').distinct().count() #가공식품을 먹은 끼니 수
    meals_with_product_ratio = round(meals_with_product_count/meal_number * 100, 2) #가공식품을 먹은 끼니 비율(%)
    
    if meals_with_product_ratio < 20:
        meals_with_product_message = "가공식품을 매우 조금만 드시는군요! 아주 좋은 식습관이에요!"
    elif meals_with_product_ratio < 40:
        meals_with_product_message = "가공식품을 조절하는게 느껴지네요! 꾸준히 신선식품도 먹어주도록 해요!"
    elif meals_with_product_ratio < 60:
        meals_with_product_message = "가공식품을 꽤 드시는 편이네요. 신경 쓰기 어렵지만 그래도 노력해봐요!"
    elif meals_with_product_ratio < 80:
        meals_with_product_message = "가공식품을 많이 드시는 편이네요. 과한 가공식품 섭취는 건강에 문제가 될 수 있어요."
    else:
        meals_with_product_message = "가공식품을 매우 많이 드시는 편이에요. 조금이라도 신선식품을 챙겨 먹을 필요가 있어요."

    #--------------------------------------------------여기부터 category_status 계산-----------------------------------------------------------
    category_rows = (
        diet_query_set
        .values('food__food_category')
        .annotate(count=Count('diet_id'))
        .order_by('-count')
    )

    # #나중에 프론트랑 상의해서 상위 몇개의 데이터를 전달할 지 정해지면 정렬이랑 슬라이싱도 구현할게요!
    category_status = [
        {'food_category': r['food__food_category'], 'count': r['count']}
        for r in category_rows
    ]

    #--------------------------------------------------여기부터 나머지 값들 한번에 계산-----------------------------------------------------------
    meal_time_stats = {"breakfast_count": 0, "lunch_count": 0, "dinner_count": 0} #아침, 점심, 저녁에 총 몇개의 가공식품을 먹었는지 저장
    weekday_stats = {"Sunday": 0, "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0} #월~일 별로 몇개의 가공식품을 먹었는지 저장

    # 날짜 범위 초기화
    calorie_by_date = {}
    cur_date = start_date
    while cur_date <= end_date:
        calorie_by_date[cur_date] = 0.0
        cur_date += timedelta(days=1)

    # 칼로리 누적
    for diet in diet_query_set:
        food = diet.food
        calorie_by_date[diet.date] += get_real_nutrient(food, "calorie")
        weekday_stats[diet.date.strftime("%A")] += 1

    # daily_data 생성
    daily_data = [{"date": d, "calorie": c} for d, c in sorted(calorie_by_date.items())]

    # 최대/최소/표준편차
    max_data = max(daily_data, key=lambda x: x["calorie"]) if daily_data else {"date": None, "calorie": 0}
    min_data = min(daily_data, key=lambda x: x["calorie"]) if daily_data else {"date": None, "calorie": 0}
    stdev = round(pstdev(d["calorie"] for d in daily_data) if daily_data else 0.0, 2)

    meal_counts = diet_query_set.aggregate(
        breakfast_count=Count('diet_id', filter=Q(meal='아침')),
        lunch_count=Count('diet_id',    filter=Q(meal='점심')),
        dinner_count=Count('diet_id',   filter=Q(meal='저녁')),
    )
    meal_time_stats = {
        "breakfast_count": meal_counts["breakfast_count"] or 0,
        "lunch_count": meal_counts["lunch_count"] or 0,
        "dinner_count": meal_counts["dinner_count"] or 0,
    }

    #API 명세 response에 명시해 둔 meal_pattern_analysis 구현 완료
    meal_pattern_analysis = {
        "meal_time_stats" : meal_time_stats,
        "weekday_stats": weekday_stats
    }
    #--------------------------------------------------여기부터 context 반환-----------------------------------------------------------
    context = {
        "start_date": start_date,
        "end_date": end_date,
        "meal_product_analysis": {
            "meal_number": meal_number,
            "product_number": product_number,
            "meals_with_product_count": meals_with_product_count,
            "meals_with_product_ratio": meals_with_product_ratio,
            "meals_with_product_message": meals_with_product_message,
            "category_status": category_status
        },
        "calorie_trend": {
            "start_date": start_date,
            "end_date": end_date,
            "daily_data": daily_data,
            "max_data": max_data,
            "min_data": min_data,
            "std_dev": stdev,
            "summary_message": stdev_summary(stdev)
        },
        "meal_pattern_analysis": meal_pattern_analysis,
    }

    #나중에 프론트에서 diet_analysis.html 같은 템플릿 만들고 나면 아래 주석처리 해놓은 render 함수로 바꿔 사용해주세요!
    return render(request, "analysis/analysis_diet.html", context)
    #return JsonResponse(context, json_dumps_params={'ensure_ascii': False})


NUTRIENTS = [
    "calorie","protein","fat","carbohydrate","sugar","dietary_fiber",
    "calcium","iron_content","phosphorus","potassium","salt",
    "VitaminA","VitaminB","VitaminC","VitaminD","VitaminE",
    "cholesterol","saturated_fatty_acids","trans_fatty_acids",
]

#더 다양한 영양소에 대한 통계치 분석
def analysis_nutrients(request):

    user = request.user

    try:
        #url에서 쿼리로 주어진 start_date, end_date
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    # 쿼리가 제대로 된 형식으로 주어지지 않았을 경우 예외처리
    except Exception:
        return HttpResponseBadRequest("날짜 형식이 잘못 되었습니다. YYYY-MM-DD 형식을 사용해 주세요.")
    
    # 분석 시작 날짜가 끝 날짜보다 뒤인 경우 예외처리
    if start_date > end_date:
        return HttpResponseBadRequest("분석 시작 날짜는 끝 날짜보다 이전이어야 합니다.")
    
    day_difference = (end_date - start_date).days + 1 #몇 일 차이인지 계산(양 끝 날짜 포함)

    #평균을 구할 영양소들 쿼리문 저장
    aggregates_kwargs = {
        f"total_{n}": Coalesce(Sum(F(f"food__{n}")), 0.00)
        for n in NUTRIENTS
    }

    #실제 평균을 구하는 쿼리
    aggregates = (
        Diet.objects
        .filter(user=user, date__range=(start_date, end_date))
        .aggregate(**aggregates_kwargs)
        )
    
    #aggregates로부터 값들 뽑아내서 context로 반환
    context = {
        f"avg_{n}_per_day": (
            float(aggregates[f"total_{n}"]) / day_difference if day_difference else 0.00
        )
        for n in NUTRIENTS
    }

    #나중에 프론트에서 diet_analysis.html 같은 템플릿 만들고 나면 아래 주석처리 해놓은 render 함수로 바꿔 사용해주세요!
    return render(request, "analysis/analysis_nutrients.html", context)
    #return JsonResponse(context, json_dumps_params={'ensure_ascii': False})
    