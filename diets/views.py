from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

#유저 식사 리스트 전달
def diet_main(request):
    return

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
def diet_fix(request, diet_id):
    return