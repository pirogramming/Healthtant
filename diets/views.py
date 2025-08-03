from django.shortcuts import render
from django.http import JsonResponse
from .models import Diet
from django.contrib.auth.decorators import login_required

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

    #JSON 반환
    return JsonResponse({
        "user_id": str(user.id),
        "year": year,
        "month": month,
        "data": data_list
    }, json_dumps_params={'ensure_ascii': False})

#유저가 최근 먹은 식품 리스트 전달
def diet_list(request):
    return

#유저가 식품 이름으로 검색하는 기능
def diet_search(request):
    return

#식사 생성
def diet_create(request, food_id):
    return

#식사 수정/삭제
def diet_update(request, diet_id):
    return