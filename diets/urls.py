from django.contrib import admin
from django.urls import path, include
from diets import views

urlpatterns = [
    path('', views.diet_main),
    path('list/', views.diet_list),
    path('search/', views.diet_search),
    path('<uuid:diet_id>/', views.diet_update, name='diet_update'),
    path('<uuid:food_id>/', views.diet_create, name='diet_create'),
    path('search/page/', views.diet_search_page),
    path('upload/', views.diet_upload),
    path('form/<uuid:diet_id>/', views.diet_form),
]