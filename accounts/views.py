from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def basic_login(request):
    if request.method == "POST":
        # 로그인 로직 작성
        return JsonResponse({"message": "기본 로그인 성공"})
    return JsonResponse({"error": "Invalid request"}, status=400)

import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User
from .models import UserProfile

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
            profile = request.user.profile

            profile.nickname = request.POST.get("nickname")
            profile.user_gender = request.POST.get("user_gender")
            profile.user_age = int(request.POST.get("user_age"))
            profile.profile_image_url = request.POST.get("profile_image_url", "default.png")
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


@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            nickname = data.get("nickname")
            gender = data.get("user_gender", "OTHER")
            age = data.get("user_age", 20)

            # 사용자 중복 확인
            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "이미 존재하는 아이디입니다."}, status=400)
            if UserProfile.objects.filter(nickname=nickname).exists():
                return JsonResponse({"error": "이미 존재하는 닉네임입니다."}, status=400)

            # User 생성
            user = User.objects.create_user(username=username, email=email, password=password)

            # UserProfile 업데이트
            profile = user.profile
            profile.nickname = nickname
            profile.user_gender = gender
            profile.user_age = age
            profile.profile_image_url = data.get("profile_image_url", "default.png")
            profile.save()

            return JsonResponse({"message": "회원가입 성공", "user_id": user.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


def check_nickname(request):
    nickname = request.GET.get("nickname")
    if not nickname:
        return JsonResponse({"error": "닉네임이 필요합니다."}, status=400)

    exists = UserProfile.objects.filter(nickname=nickname).exists()
    return JsonResponse({"available": not exists})