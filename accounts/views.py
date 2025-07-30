# accounts/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

# 기본 로그인
@csrf_exempt
def basic_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'message': '로그인 성공'})
        return JsonResponse({'error': '아이디 또는 비밀번호 오류'}, status=400)
    return JsonResponse({'error': 'POST 요청 필요'}, status=405)

# 소셜 로그인 (카카오/네이버 연동 예정)
@csrf_exempt
def social_login(request):
    if request.method == 'POST':
        # django-allauth와 연동 → 자동 처리
        return JsonResponse({'message': '소셜 로그인 처리 중'})
    return JsonResponse({'error': 'POST 요청 필요'}, status=405)

# 회원가입
@csrf_exempt
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': '이미 존재하는 아이디'}, status=400)
        user = User.objects.create_user(username=username, email=email, password=password)
        return JsonResponse({'message': '회원가입 성공', 'username': user.username})
    return JsonResponse({'error': 'POST 요청 필요'}, status=405)

# 회원 추가 정보 입력
@csrf_exempt
def profile(request):
    if request.method == 'POST':
        # 사용자 추가 정보 (예: MBTI, 나이대) 업데이트 로직
        return JsonResponse({'message': '추가 정보 입력 완료'})
    return JsonResponse({'error': 'POST 요청 필요'}, status=405)