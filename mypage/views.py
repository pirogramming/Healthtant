from django.shortcuts import render, redirect
import os
from uuid import uuid4
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.core.files.storage import default_storage
from accounts.models import UserProfile
from foods.models import FavoriteFood

@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    회원 정보 조회(GET) + 수정(POST)  // 렌더링 전용
    """
    # 로그인 상태 확인
    if not request.user.is_authenticated:
        # 로그인 안 된 경우 빈 데이터로 렌더링
        user_data = {
            "user_id": "",
            "nickname": "",
            "user_name": "",
            "user_gender": "M",
            "user_age": 25,
            "user_email": "",
            "profile_image_url": "",
        }
        return render(request, 'mypage/mypage_profile.html', {'user_data': user_data})
    
    # 로그인된 경우 기존 로직 실행
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"nickname": user.username}
    )

    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        user_age = request.POST.get('user_age')
        user_gender = request.POST.get('user_gender')
        profile_image_url = request.POST.get('profile_image_url')

        if nickname:
            profile.nickname = nickname
        if user_age:
            profile.user_age = user_age
        if user_gender:
            profile.user_gender = user_gender
        if profile_image_url:
            profile.profile_image_url = profile_image_url
        profile.save()

        messages.success(request, '프로필이 업데이트되었습니다.')
        return redirect('mypage:profile')

    # GET: 화면 렌더링
    user_data = {
        "user_id": str(user.id),
        "nickname": profile.nickname or user.username,
        "user_name": user.first_name or user.username,
        "user_gender": profile.user_gender or 'M',
        "user_age": profile.user_age or 25,
        "user_email": user.email,
        "profile_image_url": profile.profile_image_url or "",
    }
    return render(request, 'mypage/mypage_profile.html', {'user_data': user_data})

MAX_MB = 5

def _save_image_and_get_url(file, user_id):
    ext = os.path.splitext(file.name)[1].lower()
    path = f"profiles/{user_id}/{uuid4()}{ext}"
    saved = default_storage.save(path, file)         
    return getattr(default_storage, "url", None)(saved) if hasattr(default_storage, "url") \
           else f"{settings.MEDIA_URL}{saved}"

@login_required(login_url='/accounts/login/')
@require_POST
def upload_profile_image(request):
    f = request.FILES.get("profile_image")
    if not f:
        return JsonResponse({"success": False, "error": "파일이 없습니다."}, status=400)
    if not str(f.content_type).startswith("image/"):
        return JsonResponse({"success": False, "error": "이미지 파일만 허용됩니다."}, status=400)
    if f.size > MAX_MB * 1024 * 1024:
        return JsonResponse({"success": False, "error": f"{MAX_MB}MB 이하만 업로드 가능합니다."}, status=400)

    image_url = _save_image_and_get_url(f, request.user.id)

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user, defaults={"nickname": request.user.username}
    )
    profile.profile_image_url = image_url
    profile.save(update_fields=["profile_image_url"])

    return JsonResponse({"success": True, "image_url": image_url})


@login_required(login_url='/accounts/login/')
def favorite_food_list(request):
    """
    즐겨찾는 제품 목록 조회 (GET) // 렌더링 전용
    """
    favorites = (FavoriteFood.objects
                 .filter(user=request.user)
                 .select_related('food'))
    favorite_foods = []
    for f in favorites:
        food = f.food
        favorite_foods.append({
            "favorite_id": str(f.pk),
            "food_id": str(food.food_id),
            "food_name": food.food_name,
            "food_img": getattr(food, 'food_img', '') or "http://example.com/default_food.png",
            "company_name": getattr(food, 'company_name', '') or "Unknown",
            "calorie": int(food.calorie) if getattr(food, 'calorie', None) else 0,
            "created_at": getattr(f, 'created_at', None),
        })
    return render(request, 'mypage/mypage_favorite_foods.html', {'favorites': favorite_foods})


@login_required(login_url='/accounts/login/')
@require_POST
def favorite_food_delete(request, food_id):
    """
    즐겨찾는 제품 취소 (POST) // 렌더링 전용
    """
    try:
        fav = FavoriteFood.objects.get(user=request.user, food__food_id=food_id)
        fav.delete()
        messages.success(request, '즐겨찾기가 취소되었습니다.')
    except FavoriteFood.DoesNotExist:
        messages.error(request, '해당 즐겨찾기를 찾을 수 없습니다.')
    return redirect('mypage:favorite_food_list')


@login_required(login_url='/accounts/login/')
@require_http_methods(["GET", "POST"])
def account_withdraw(request):
    if request.method == 'POST':
        # 현재 로그인한 유저 완전 삭제
        request.user.delete()
        logout(request)  # 삭제 후 세션 종료
        messages.success(request, '회원 탈퇴가 완료되었습니다.')
        return redirect('main:main_page')
    return render(request, 'mypage/mypage_withdraw_confirm.html', {'user': request.user})