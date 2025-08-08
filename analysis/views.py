from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from diets.models import Diet
from datetime import datetime
from django.http import JsonResponse

#user의 각 영양소별 필수섭취량, 적정량 범위를 구하는 메소드
def calculate_recommendation(user):
    gender = user.profile.user_gender
    age = user.profile.user_age

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
    ret['protein']['essential'] = protein_table[idx][0] if gender == "남성" else protein_table[idx][1] #필수 단백질 양
    ret['salt']['essential'] = min_salt_table[idx] #필수 나트륨 양

    recommend_calorie = eer_table[idx][0] if gender == "남성" else eer_table[idx][1] #유저의 필요 에너지 추정량 계산

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
        return "#ffbb00"
    else:
        return "#56aab2"

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

@login_required
def analysis_main(request):
    user = request.user

    #url에서 쿼리로 주어진 start_date, end_date
    start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    day_difference = (end_date - start_date).days + 1 #몇 일 차이인지 계산(양 끝 날짜 포함)

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
        nutrients_avg['calorie'] += food.calorie / food.nutritional_value_standard_amount * food.serving_size
        nutrients_avg['carbohydrate'] += food.carbohydrate / food.nutritional_value_standard_amount * food.serving_size
        nutrients_avg['protein'] += food.protein / food.nutritional_value_standard_amount * food.serving_size
        nutrients_avg['fat'] += food.fat / food.nutritional_value_standard_amount * food.serving_size
        nutrients_avg['salt'] += food.salt / food.nutritional_value_standard_amount * food.serving_size

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
        "nutrients_evaluation": nutrient_evaluation
    }

    #나중에 프론트에서 main.html 같은 템플릿 만들고 나면 아래 주석처리 해놓은 render 함수로 바꿔 사용해주세요!
    #return render(request, "analysis/analysis_main.html", context)
    return JsonResponse(context, json_dumps_params={'ensure_ascii': False})