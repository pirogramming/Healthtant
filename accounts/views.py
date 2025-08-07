import json
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UserProfile


@csrf_exempt
@login_required
def profile(request):
    if request.method == "GET":
        if request.session.get("just_signed_up", False):
            request.session["just_signed_up"] = False
            return render(request, 'accounts/profile.html', {
                "user": request.user,
                "profile": request.user.profile,
            })
        return redirect("/")

    elif request.method == "POST":
        try:
            profile = request.user.profile

            profile.nickname = request.POST.get("nickname")
            profile.user_gender = request.POST.get("user_gender")
            profile.user_age = request.POST.get("user_age")
            # 프로필 이미지 URL은 추후 파일 업로드 처리 방식에 따라 별도 처리 가능
            profile.save()

            return JsonResponse({"message": "회원 정보 수정 성공", "redirect": "/"})
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
            gender = data.get("user_gender")
            age = data.get("user_age")

            # 중복 체크
            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "이미 존재하는 아이디입니다."}, status=400)
            if UserProfile.objects.filter(nickname=nickname).exists():
                return JsonResponse({"error": "이미 존재하는 닉네임입니다."}, status=400)

            # User 생성 및 프로필 설정
            user = User.objects.create_user(username=username, email=email, password=password)
            profile = user.profile
            profile.nickname = nickname
            profile.user_gender = gender
            profile.user_age = age
            profile.profile_image_url = data.get("profile_image_url", "default.png")
            profile.save()

            # 로그인 처리 및 플래그 설정
            login(request, user)
            request.session["just_signed_up"] = True

            return redirect("/accounts/profile/")
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

'''
def check_nickname(request):
    nickname = request.GET.get("nickname")
    if not nickname:
        return JsonResponse({"error": "닉네임이 필요합니다."}, status=400)

    exists = UserProfile.objects.filter(nickname=nickname).exists()
    return JsonResponse({"available": not exists})
    '''