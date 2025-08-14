from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('test-400/', views.bad_request_view, name='test_400'),
    path('test-403/', views.permission_denied_view, name='test_403'),
    path('test-404/', views.not_found_view, name='test_404'),
    path('test-500/', views.server_error_view, name='test_500'),
]