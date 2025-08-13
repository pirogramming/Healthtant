# config/settings/base.py
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.google',

    'accounts',
    'diets',
    'foods',
    'main',
    'analysis',
    'products',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/profile/'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_ADAPTER = "accounts.adapters.CustomAccountAdapter"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 미디어 파일 설정 (업로드된 파일 저장)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SOCIALACCOUNT_LOGIN_ON_GET = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SOCIALACCOUNT_PROVIDERS = {
    'kakao': {
        'APP': {
            'client_id': os.getenv('KAKAO_REST_API_KEY'),
            'secret': '',
            'key': ''
        }
    },
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'}
    },
}

# CSRF 보안 설정
CSRF_COOKIE_SECURE = True  # HTTPS에서만 쿠키 전송
CSRF_COOKIE_SAMESITE = 'Lax'  # 또는 'None' (CORS가 필요하면 'None' + HTTPS 필수)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF 신뢰 도메인 등록 (반드시 도메인 프로토콜 포함!)
CSRF_TRUSTED_ORIGINS = [
    'https://healthtant.com',
]

SECURE_SSL_REDIRECT = False