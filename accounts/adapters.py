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
        request.session["just_signed_up"] = True
        return "/accounts/profile/"
    
    def get_login_redirect_url(self, request):
        return "/accounts/profile/"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # 소셜 로그인 시 UserProfile 생성
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=user,
                nickname=user.username or sociallogin.account.extra_data.get('name', 'Social User'),
                user_gender=None,
                user_age=None
            )
        return user
    
    def get_signup_redirect_url(self, request):
        request.session["just_signed_up"] = True
        return "/accounts/profile/"