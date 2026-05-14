import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tiktak-ai-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    # Our apps
    'apps.gateway',
    'apps.crm',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.crm.authentication.JWTCompanyAuthentication',
        'apps.crm.authentication.StaticTokenAuthentication',
    ],
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.AutoLoginMiddleware',  # Auto-login en /admin/ en mode DEBUG
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'tiktak'),
        'USER': os.getenv('POSTGRES_USER', ''),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{os.getenv("REDIS_HOST", "redis")}:{os.getenv("REDIS_PORT", "6379")}/1',
    }
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3010"
]


# Trusted origins for CSRF — must include all domains that POST to Django
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'https://chat.tiktakpro.com,https://ai.tiktakpro.com'
    ).split(',')
    if origin.strip()
]

# ======= External Services =======
# Gemini LLM Direct Mode
GEMINI_API_KEY                       = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL                         = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Vision Service (CLIP + pgvector)
VISION_SERVICE_URL   = os.getenv('VISION_SERVICE_URL',   'http://vision-service:8002')
VISION_SEARCH_PATH   = os.getenv('VISION_SEARCH_PATH',   '/search-similar')

# TikTak Real API (External product catalog)
TIKTAK_API_BASE_URL      = os.getenv('TIKTAK_API_BASE_URL',     'https://api.tiktakpro.com')
TIKTAK_API_PRODUCTS_PATH = os.getenv('TIKTAK_API_PRODUCTS_PATH', '/api/v1/products-read/')
TIKTAK_API_TOKEN         = os.getenv('TIKTAK_API_TOKEN',         '')
PRODUCTS_CACHE_TTL       = int(os.getenv('PRODUCTS_CACHE_TTL',   '900'))  # 15 min (longer window → better Gemini implicit cache hits)

# Request timeouts (seconds)
EXTERNAL_REQUEST_TIMEOUT = int(os.getenv('EXTERNAL_REQUEST_TIMEOUT', '5'))

# ============================================================
# META WEBHOOK CONFIGURATION (Messenger / Instagram)
# ============================================================

# Token used by Meta to verify the webhook endpoint (GET request)
META_VERIFY_TOKEN = os.getenv('META_VERIFY_TOKEN', '')
META_APP_SECRET   = os.getenv('META_APP_SECRET', '')


# ============================================================
# FIELD ENCRYPTION (Fernet AES-128-CBC)
# ============================================================
# Used to encrypt sensitive fields: meta_page_access_token, gemini_api_key
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')


# ============================================================
# STATIC FILES
# ============================================================
STATIC_URL = '/static/'  # single canonical declaration
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# JWT AUTHENTICATION (simplejwt)
# ============================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
