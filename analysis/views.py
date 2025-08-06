from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from diets.models import Diet
from datetime import datetime

def calculate_recommendation(user):
    gender = user.gender  # '남성' 또는 '여성'
    age = user.age        # int

    ret = {
        'calorie': 0,
        'carbohydrate': 0,
        'protein': 0,
        'salt': 0
    }

    age_interval = [(1,2), (3,5), (6,8), (9,11), (12,14), (15,18), (19,29), (30,49), (50,64), (65,74), (75,150)]
    for i in range(len(age_interval)):
        start, end = age_interval[i]
        if start <= age <= end:
            idx = i
            break
    
    # 에너지 필요추정량 표
    eer_table = [
        (900, 900),
        (1400, 1400),
        (1700, 1500),
        (2000, 1800),
        (2500, 2100),
        (2700, 2000),
        (2600, 2000),
        (2600, 2000),
        (2400, 1900),
        (2200, 1800),
        (2000, 1600)
    ]

    # 단백질 권장량 (g)
    protein_table = [
        (15, 15),
        (20, 20),
        (30, 25),
        (40, 35),
        (55, 45),
        (60, 50),
        (60, 50),
        (60, 50),
        (60, 50),
        (60, 50),
        (60, 50)
    ]

    salt_table = [
        1200,
        1600,
        1900,
        2300,
        2300,
        2300,
        2300,
        2300,
        2300,
        2300,
        1700
    ]

    ret['calorie'] = eer_table[idx][0] if gender == "남성" else eer_table[idx][1]
    ret['carbohydrate'] = 130 #탄수화물 권장섭취량 130g으로 고정됨
    ret['protein'] = protein_table[idx][0] if gender == "남성" else protein_table[idx][1]
    ret['salt'] = salt_table[idx] #만성질환 위험감소 섭취량은 남성과 여성이 동일

    return ret


@login_required
def analysis_main(request):
    user = request.user

    #url에서 쿼리로 주어진 start_date, end_date
    start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    day_difference = (end_date - start_date).days + 1 #몇 일 차이인지 계산(양 끝 날짜 포함)

    # 아직 PostgreSQL을 쓰고 있지 않아서 이 부분은 주석처리 했습니다. (PostgreSQL 에서만 distinct를 지원한다고 합니다!)
    # meal_number = Diet.objects.filter(
    #     user=request.user,
    #     date__range=(start_date, end_date)
    # ).values('date', 'meal').distinct().count()

    #자주 쓰게 될 쿼리셋을 미리 조회해서 저장해둠
    diet_query_set = Diet.objects.select_related('food').filter(
        user=request.user,
        date__range=(start_date, end_date)
    )

    #--------------------------------------------------여기부터 meal_number 계산-----------------------------------------------------------
    meal_number = len(set(diet_query_set.values_list('date', 'meal'))) #끼니 수 계산

    #--------------------------------------------------여기부터 product_number 계산-----------------------------------------------------------
    #start_date - end_date 동안 먹은 가공식품의 수 계산
    product_number = diet_query_set.count()

    #--------------------------------------------------여기부터 category_status 계산-----------------------------------------------------------
    #식품분류 : 섭취횟수 로 매핑할 딕셔너리
    category_count_dict = dict()
    for diet in diet_query_set:
        food = diet.food #현재 보고 있는 diet의 식품
        category = food.food_category #식품의 식품분류명
        value = category_count_dict.get(category, 0) #지금까지 카운팅 된 값(default:0)을 가져옴
        category_count_dict[category] = value+1 #1회 추가(카운팅)
    
    #api 명세에 기록한 형태로 데이터 가공
    category_status = []
    for category, count in category_count_dict.items():
        category_status.append({'food_category': category, 'count': count})

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
        nutrients_avg['calorie'] += food.calorie
        nutrients_avg['carbohydrate'] += food.carbohydrate
        nutrients_avg['protein'] += food.protein
        nutrients_avg['fat'] += food.fat
        nutrients_avg['salt'] += food.salt

    for nutrient, sum in nutrients_avg.items():
        nutrients_avg[nutrient] = round(sum/day_difference, 2)

    #--------------------------------------------------여기부터 recommend_nutrients 계산-----------------------------------------------------------



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
    }