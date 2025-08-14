from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

# API 라우터 설정
router = DefaultRouter()
router.register(r'foods', api_views.FoodViewSet)
router.register(r'prices', api_views.PriceViewSet)

app_name = 'foods'

urlpatterns = [
    # 기존 웹 뷰
    path('', views.food_list, name='food_list'),
    path('<str:food_id>/', views.food_detail, name='food_detail'),
    
    # 새로운 /db/ 엔드포인트 (POST 방식)
    path('db/', api_views.DatabaseAPIView.as_view(), name='database_api'),
    
    # 기존 API 엔드포인트
    path('api/', include(router.urls)),
] 