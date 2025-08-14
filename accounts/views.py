# accounts/views.py
import json
import os
from uuid import uuid4

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse

from django.conf import settings
from django.core.files.storage import default_storage

from .models import UserProfile


MAX_MB = 5

def _save_image_and_get_url(file, user_id):
    if not str(file.content_type).startswith("image/"):
        raise ValueError("이미지 파일만 업로드 가능합니다.")
    if file.size > MAX_MB * 1024 * 1024:
        raise ValueError(f"{MAX_MB}MB 이하만 업로드 가능합니다.")

    ext = os.path.splitext(file.name)[1].lower()
    path = f"profiles/{user_id}/{uuid4()}{ext}"
    saved = default_storage.save(path, file)
    return default_storage.url(saved) if hasattr(default_storage, "url") else f"{settings.MEDIA_URL}{saved}"


@csrf_exempt
@login_required(login_url='/accounts/login/')
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

            profile.nickname    = request.POST.get("nickname") or profile.nickname
            profile.user_gender = request.POST.get("user_gender") or profile.user_gender
            profile.user_age    = request.POST.get("user_age") or profile.user_age

            if request.FILES.get("profile_image"):
                image_url = _save_image_and_get_url(request.FILES["profile_image"], request.user.id)
                profile.profile_image_url = image_url

            profile.save()

            return redirect('/mypage/?saved=1')

        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
@login_required(login_url='/accounts/login/')
def profile_edit(request):
    if request.method == "GET":
        return render(request, 'accounts/profile_edit.html', {
            "user": request.user,
            "profile": request.user.profile,
        })
    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            username = request.POST.get("username")
            email    = request.POST.get("email")
            password = request.POST.get("password")
            nickname = request.POST.get("nickname")
            gender   = request.POST.get("user_gender")
            age      = request.POST.get("user_age")

            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "이미 존재하는 아이디입니다."}, status=400)
            if UserProfile.objects.filter(nickname=nickname).exists():
                return JsonResponse({"error": "이미 존재하는 닉네임입니다."}, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            profile = user.profile
            profile.nickname = nickname
            profile.user_gender = gender
            profile.user_age = age

            if request.FILES.get("profile_image"):
                image_url = _save_image_and_get_url(request.FILES["profile_image"], user.id)
                profile.profile_image_url = image_url
            else:
                profile.profile_image_url = "default.png"

            profile.save()

            login(request, user)
            request.session["just_signed_up"] = True
            return redirect("/accounts/profile/")

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

'''
def check_nickname(request):
    nickname = request.GET.get("nickname")
    if not nickname:
        return JsonResponse({"error": "닉네임이 필요합니다."}, status=400)

    exists = UserProfile.objects.filter(nickname=nickname).exists()
    return JsonResponse({"available": not exists})
    '''