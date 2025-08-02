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

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@csrf_exempt
@login_required
def profile(request):
    if request.method == "GET":
        # profile.html 렌더링
        return render(request, 'accounts/profile.html', {
            "user": request.user,
            "profile": getattr(request.user, "profile", None)
        })

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            profile = request.user.profile

            profile.nickname = data.get("nickname")
            profile.user_gender = data.get("user_gender")
            profile.user_age = data.get("user_age")
            profile.profile_image_url = data.get("profile_image_url")
            profile.save()

            return JsonResponse({
                "message": "회원 정보 수정 성공",
                "user_id": request.user.id,
                "nickname": profile.nickname,
                "user_gender": profile.user_gender,
                "user_age": profile.user_age,
                "profile_image_url": profile.profile_image_url,
                "user_email": request.user.email,
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def check_nickname(request):
    nickname = request.GET.get("nickname")
    if nickname == "abc":  # 예시
        return JsonResponse({"available": False})
    return JsonResponse({"available": True})
