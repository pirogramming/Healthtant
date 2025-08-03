from django.contrib import admin
from django.urls import path, include
from diets import views

urlpatterns = [
    path('', views.diet_main),
    path('list/', views.diet_list),
    path('search/', views.diet_search),
    path('<str:food_id>/', views.diet_create),
    path('<str:diet_id>/', views.diet_update),
]