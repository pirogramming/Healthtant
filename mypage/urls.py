from django.urls import path
from . import views

app_name = 'mypage'

urlpatterns = [
    path('', views.profile_view, name='profile_view'), # 회원 정보 목록 및 회원 정보 수정
    path('upload-image/', views.upload_profile_image, name='upload_profile_image'), # 프로필 이미지 업로드
    path('food/like/', views.favorite_food_list, name='favorite_food_list'), # 즐겨찾는 제품 목록
    path('food/like/<str:food_id>/', views.favorite_food_delete, name='favorite_food_delete'), # 즐겨찾는 제품 취소
    path('withdraw/', views.account_withdraw, name='account_withdraw'), # 탈퇴하기
]