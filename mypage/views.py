from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from foods.models import FavoriteFood
import os

@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    회원 정보 조회(GET) + 수정(POST)  // 렌더링 전용
    """
    user = request.user

    if request.method == 'POST':
        # form 제출 값 사용
        nickname = request.POST.get('nickname')
        user_age = request.POST.get('user_age')
        user_gender = request.POST.get('user_gender')
        profile_image_url = request.POST.get('profile_image_url')

        if nickname:
            if hasattr(user, 'nickname'):
                user.nickname = nickname
            else:
                user.username = nickname
        if user_age and hasattr(user, 'user_age'):
            user.user_age = user_age
        if user_gender and hasattr(user, 'user_gender'):
            user.user_gender = user_gender
        if profile_image_url and hasattr(user, 'user_image'):
            user.user_image = profile_image_url
        user.save()

        if hasattr(user, 'profile'):
            profile = user.profile
            if nickname: profile.nickname = nickname
            if user_age: profile.user_age = user_age
            if user_gender: profile.user_gender = user_gender
            if profile_image_url: profile.user_image = profile_image_url
            profile.save()

        messages.success(request, '프로필이 업데이트되었습니다.')
        return redirect('mypage:profile')  # url name에 맞게 변경

    # GET: 화면 렌더링
    profile_image_url = ""
    if hasattr(user, 'profile') and user.profile.profile_image:
        profile_image_url = user.profile.profile_image.url
    elif hasattr(user, 'profile') and user.profile.profile_image_url:
        profile_image_url = user.profile.profile_image_url
    
    user_data = {
        "user_id": str(user.id),
        "nickname": getattr(user, 'nickname', user.username),
        "user_name": user.first_name or user.username,
        "user_gender": getattr(user, 'user_gender', 'M'),
        "user_age": getattr(user, 'user_age', 25),
        "user_email": user.email,
        "profile_image_url": profile_image_url
    }
    if hasattr(user, 'profile'):
        p = user.profile
        user_data.update({
            "nickname": getattr(p, 'nickname', user.username),
            "user_gender": getattr(p, 'user_gender', 'M'),
            "user_age": getattr(p, 'user_age', 25),
            "profile_image_url": profile_image_url
        })
    return render(request, 'mypage/mypage_profile.html', {'user_data': user_data})


@login_required
@require_POST
def upload_profile_image(request):
    """
    프로필 이미지 업로드 (AJAX) - 별도 엔드포인트
    """
    try:
        if 'profile_image' not in request.FILES:
            return JsonResponse({'success': False, 'error': '이미지 파일이 없습니다.'})
        
        profile_image = request.FILES['profile_image']
        
        # 파일 검증
        if profile_image.size > 5 * 1024 * 1024:  # 5MB 제한
            return JsonResponse({'success': False, 'error': '파일 크기가 너무 큽니다. (최대 5MB)'})
        
        if not profile_image.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': '이미지 파일만 업로드 가능합니다.'})
        
        # 사용자 프로필 가져오기 또는 생성
        user = request.user
        if not hasattr(user, 'profile'):
            from accounts.models import UserProfile
            profile = UserProfile.objects.create(
                user=user,
                nickname=user.username,
            )
        else:
            profile = user.profile
        
        # 기존 이미지 파일 삭제 (선택사항)
        if profile.profile_image:
            if os.path.exists(profile.profile_image.path):
                os.remove(profile.profile_image.path)
        
        # 새 이미지 저장
        profile.profile_image = profile_image
        profile.save()
        
        return JsonResponse({
            'success': True, 
            'image_url': profile.profile_image.url,
            'message': '프로필 이미지가 업데이트되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'업로드 중 오류가 발생했습니다: {str(e)}'})


@login_required
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
            "favorite_id": f.id,
            "food_id": str(food.food_id),
            "food_name": food.food_name,
            "food_img": getattr(food, 'food_img', '') or "http://example.com/default_food.png",
            "company_name": getattr(food, 'company_name', '') or "Unknown",
            "calorie": int(food.calorie) if getattr(food, 'calorie', None) else 0,
            "created_at": getattr(f, 'created_at', None),
        })
    return render(request, 'mypage/mypage_favorite_foods.html', {'favorites': favorite_foods})


@login_required
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
    return redirect('mypage:favorites')  # 목록 화면으로


@login_required
@require_http_methods(["GET", "POST"])
def account_withdraw(request):
    """
    회원 탈퇴 (GET 확인 페이지, POST 실제 탈퇴) // 렌더링 전용
    """
    if request.method == 'POST':
        user = request.user
        # 비활성화(권장)
        user.is_active = False
        user.save()
        logout(request)
        messages.success(request, '회원 탈퇴가 완료되었습니다.')
        return redirect('main:main_page')  # 메인 페이지로
    return render(request, 'mypage/mypage_withdraw_confirm.html', {'user': request.user})