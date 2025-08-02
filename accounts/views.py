from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def basic_login(request):
    if request.method == "POST":
        # 로그인 로직 작성
        return JsonResponse({"message": "기본 로그인 성공"})
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def signup(request):
    if request.method == "POST":
        # 회원가입 로직 작성
        return JsonResponse({"message": "회원가입 성공"})
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def update_profile(request):
    if request.method == "PATCH":
        # 회원 정보 업데이트 로직 작성
        return JsonResponse({"message": "회원 정보 수정 성공"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def check_nickname(request):
    nickname = request.GET.get("nickname")
    if nickname == "abc":  # 예시
        return JsonResponse({"available": False})
    return JsonResponse({"available": True})

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })