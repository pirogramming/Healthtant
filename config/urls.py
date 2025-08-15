"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('diets/', include('diets.urls')),
    path('analysis/', include('analysis.urls')),
    path('products/', include('products.urls')),
    path('mypage/', include('mypage.urls')),
    #path('db/', include('db.urls')),
    path('search/', include('search.urls')),
]

# 에러 핸들러 설정
handler400 = 'main.views.bad_request_view'
handler403 = 'main.views.permission_denied_view'
handler404 = 'main.views.not_found_view'
handler500 = 'main.views.server_error_view'

# 미디어 파일 서빙 (개발 환경에서만)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)