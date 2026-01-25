"""
CloudServices India - Django Settings
=====================================
"""
from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-xyz123')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# =============================================
# INSTALLED APPS
# =============================================
INSTALLED_APPS = [
    'custom_admin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third Party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'phonenumber_field',
    'ckeditor',
    # Local Apps
    'apps.accounts',
    'apps.locations',
    'apps.categories',
    'apps.products',
    'apps.orders',
    # 'apps.payments',
    'apps.blog',
    'apps.banner',
    'apps.about',
    'apps.policy',
    'apps.privacy',
]

# =============================================
# MIDDLEWARE
# =============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# =============================================
# TEMPLATES
# =============================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'custom_admin.context_processors.admin_context'
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# =============================================
# DATABASE
# =============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =============================================
# CUSTOM USER MODEL
# =============================================
AUTH_USER_MODEL = 'accounts.User'

# =============================================
# PASSWORD VALIDATION
# =============================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# =============================================
# INTERNATIONALIZATION
# =============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# =============================================
# STATIC & MEDIA FILES
# =============================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================
# REST FRAMEWORK
# =============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =============================================
# JWT SETTINGS
# =============================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# =============================================
# CORS SETTINGS
# =============================================
CORS_ALLOW_ALL_ORIGINS = True

# =============================================
# PHONE NUMBER
# =============================================
PHONENUMBER_DEFAULT_REGION = 'IN'

# =============================================
# API DOCUMENTATION
# =============================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'CloudServices India API',
    'DESCRIPTION': 'Pan-India Digital Services Platform',
    'VERSION': '1.0.0',
}

# =============================================
# RAZORPAY SETTINGS
# =============================================
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# =============================================
# OTP SETTINGS
# =============================================
OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6
