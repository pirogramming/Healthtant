from django.contrib import admin
from django.urls import path, include
from analysis import views

urlpatterns = [
    path('', views.analysis_main),
    path('diets/', views.analysis_diet),
]