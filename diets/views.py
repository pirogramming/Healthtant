from django.shortcuts import render
from django.http import JsonResponse
from .models import Diet
from foods.models import Food
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField

#유저 식사 리스트 전달
@login_required
def diet_main(request):
    user = request.user #GET으로 받은 유저 정보
    year = int(request.GET.get('year')) #쿼리로 받은 연도(url에 포함)
    month = int(request.GET.get('month')) #쿼리로 받은 월(url에 포함)

    # Diet 모델 모두 가져오기 -> food 테이블과 JOIN -> date 기준으로 오름차순 정렬
    # food랑 JOIN을 안해주면 나중에 food.food_name으로 조회할 때마다 엄청난 양의 쿼리가 발생합니다!!
    diets = Diet.objects.filter(
        user=user,
        date__year=year,
        date__month=month
    ).select_related('food').order_by('date')

    #한글로 표시된 끼니 영어로 번역하기 위한 딕셔너리
    english_meal = {"아침": "breakfast", "점심": "lunch", "저녁": "dinner"}

    # 프론트로 넘겨줄 데이터 리스트
    data_list = []

    #현재 date에 속하는 식사가 1개도 없을 경우 바로 반환 (예외처리)
    if not diets:
        return JsonResponse({
            "user_id": str(user.id),
            "year": year,
            "month": month,
            "data": []
        }, json_dumps_params={'ensure_ascii': False})

    #--------------------여기부터 API 명세 형식에 맞게 데이터 구성해서 반환하는 부분---------------------------------
    current_date = diets[0].date #diets에서 가장 앞의 데이터(가장 빠른 데이터)를 가져와 현재 날짜로 설정
    #data_list에 append하고 시작
    data_list.append({
        "date": current_date.isoformat(),
        "diets": {"breakfast": [], "lunch": [], "dinner": []}
    })

    #diets는 이미 날짜순으로 정렬되어 있으므로 앞에서부터 담으면 자연스럽게 날짜순으로 데이터가 반환됨
    for diet in diets:
        #기존에 알던 current_date(날짜)와 지금 가져온 diet의 날짜가 다를 경우, 다음 날짜로 데이터가 넘어갔음을 의미함
        if diet.date != current_date:
            current_date = diet.date #current_date 업데이트
            #새로운 데이터셋 append
            data_list.append({
                "date": current_date.isoformat(),
                "diets": {"breakfast": [], "lunch": [], "dinner": []}
            })

        #데이터셋 추가가 끝났으므로 현재 가장 끝에 위치한 dict가 데이터를 넣을 대상이 됨
        current_dict = data_list[-1] #가장 끝에 위치한 dict
        #데이터 추가
        current_dict["diets"][english_meal[diet.meal]].append({
            "diet_id": str(diet.diet_id),
            "food_id": str(diet.food.food_id),
            "food_name": diet.food.food_name
        })

    #일단 JsonResponse 반환으로 구현해뒀는데 나중에 프론트 구현되면 render로 창 넘어갈 수 있게 구현할게요!!
    return JsonResponse({
        "user_id": user.id,
        "year": year,
        "month": month,
        "data": data_list
    }, json_dumps_params={'ensure_ascii': False})

@login_required
#유저가 최근 먹은 식품 리스트 전달
def diet_list(request):
    user = request.user

    #저녁 식사로 등록한 것이 가장 최근, 점심은 그 다음, 아침은 그 다음
    meal_ordering = Case(
        When(meal='아침', then=Value(0)),
        When(meal='점심', then=Value(1)),
        When(meal='저녁', then=Value(2)),
        output_field=IntegerField()
    )

    diets = list(Diet.objects.filter(user=user).select_related('food').order_by('date', meal_ordering))

    #유저가 등록한 식단이 없을 경우 예외처리
    if not diets:
        return JsonResponse({
            "user_id": user.id,
            "recent_foods": []
        })
    
    idx = len(diets)-1 #가장 최근의 식사부터 시작
    cnt = 0 #몇개의 제품이 append 되었는지 추적
    recent_foods = [] #데이터를 담을 리스트
    seen_food_ids = set() #중복으로 식품을 담지 않기 위해 선언한 set
    while idx >= 0 and cnt < 5 :
        diet = diets[idx] #최근 식사
        cur_food = diet.food #최근 식사에 먹은 식품
        #중복되지 않는 식품이라면 데이터에 추가
        if cur_food.food_id not in seen_food_ids:
            seen_food_ids.add(cur_food.food_id)
            recent_foods.append({
                "food_id": str(cur_food.food_id),
                "food_name" : cur_food.food_name,
                "company_name": cur_food.company_name,
                "food_img": cur_food.food_img
                })
            cnt += 1 #식품 카운팅
        idx -= 1 #다음으로 최근에 먹은 식사로 이동

    #일단은 JsonResponse를 반환하되 나중에 프론트 구현되면 render로 창 옮겨갈 수 있게 구현할게요!!
    return JsonResponse({
        "user_id": user.id,
        "recent_foods": recent_foods
    })

@login_required
#유저가 식품 이름으로 검색하는 기능
def diet_search(request):
    user = request.user
    keyword = request.GET.get('keyword', '').strip() #유저가 검색한 키워드

    foods = list(Food.objects.filter(food_name__icontains=keyword)) #keyword를 포함하는 Food 모델 모두 가져오기
    ret = {'user_id': user.id, 'foods': []} #프론트로 넘겨줄 mock data

    # 검색 결과 조회된 food를 하나씩 순회
    for food in foods:
        food_data = dict() #food의 정보를 담을 dict
        food_data['food_id'] = food.food_id
        food_data['food_name'] = food.food_name
        food_data['company_name'] = food.company_name
        food_data['food_img'] = food.food_img
        ret['foods'].append(food_data) #food_data 에 정보를 모두 담았으니 ret['foods']에 추가

    #일단은 JsonResponse를 반환하되 나중에 프론트 구현되면 render로 창 옮겨갈 수 있게 구현할게요!!
    return JsonResponse(ret, json_dumps_params={'ensure_ascii': False})

#식사 생성
def diet_create(request, food_id):
    food = Food.objects.get(food_id=food_id)
    user = request.user
    date = request.POST.get('date')
    meal = request.POST.get('meal')
    
    diet = Diet.objects.create(user=user, food=food, meal=meal, date=date) #유저가 입력한 대로 Diet 생성

    food_data = {
        'food_id': food.food_id,
        'food_name': food.food_name,
        'company_name': food.company_name
    }

    #반환할 mock data 구성!
    ret = {'diet_id': diet.diet_id, 'user_id': user.id, 'food': food_data, 'message': "새 식사 등록이 완료되었습니다."}

    #일단은 JsonResponse를 반환하되 나중에 프론트 구현되면 render로 창 옮겨갈 수 있게 구현할게요!!
    return JsonResponse(ret, json_dumps_params={'ensure_ascii': False})

#식사 수정/삭제
def diet_update(request, diet_id):
    return