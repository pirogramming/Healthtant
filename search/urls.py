from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_page, name='search_page'),
]