from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_signup_redirect_url(self, request):
        request.session["just_signed_up"] = True
        return "/accounts/profile/"
    
    def get_login_redirect_url(self, request):
        return "/accounts/profile/"