from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.basic_login, name='basic_login'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('check-nickname/', views.check_nickname, name='check_nickname'),
]