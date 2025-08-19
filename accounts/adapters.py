from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import UserProfile

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)
        if commit:
            # UserProfile이 없으면 생성
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(
                    user=user,
                    nickname=user.username,
                    user_gender=None,
                    user_age=None
                )
        return user
    
    def get_signup_redirect_url(self, request):
        # 일반 회원가입 후 바로 메인 페이지로 이동
        return "/"
    
    def get_login_redirect_url(self, request):
        return "/"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # 소셜 로그인 시 UserProfile 생성 (기본값으로)
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            # 기본 닉네임으로 UserProfile 생성 (중복 방지)
            base_nickname = f"User{user.id}"
            nickname = base_nickname
            counter = 1
            
            # 닉네임이 중복되면 숫자를 붙여서 고유하게 만들기
            while UserProfile.objects.filter(nickname=nickname).exists():
                nickname = f"{base_nickname}_{counter}"
                counter += 1
            
            UserProfile.objects.create(
                user=user,
                nickname=nickname,
                user_gender=None,
                user_age=None
            )
        return user
    
    def get_signup_redirect_url(self, request):
        # 소셜 로그인 후 바로 메인 페이지로 이동
        return "/"
    
    def get_login_redirect_url(self, request):
        # 소셜 로그인 후 바로 메인 페이지로 이동
        return "/"