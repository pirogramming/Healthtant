from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_page, name='search_page'),
    path('normal/', views.normal_search, name='normal_search'),
]