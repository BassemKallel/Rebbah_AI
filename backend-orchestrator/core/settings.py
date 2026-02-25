import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tiktak-ai-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    # Our apps
    'apps.gateway',
    'apps.crm',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'postgres-db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{os.getenv("REDIS_HOST", "tiktak-redis")}:{os.getenv("REDIS_PORT", "6379")}/1',
    }
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOW_ALL_ORIGINS = True

# ============================================================
# EXTERNAL SERVICES CONFIGURATION
# ============================================================

# NLU Service (TunBERT + GLiNER)
NLU_SERVICE_URL    = os.getenv('NLU_SERVICE_URL',    'http://nlu-service:8001')
NLU_PREDICT_PATH   = os.getenv('NLU_PREDICT_PATH',   '/predict')

# Vision Service (CLIP + pgvector)
VISION_SERVICE_URL   = os.getenv('VISION_SERVICE_URL',   'http://vision-service:8002')
VISION_SEARCH_PATH   = os.getenv('VISION_SEARCH_PATH',   '/search-similar')

# Mock API (External product catalog)
MOCK_API_BASE_URL           = os.getenv('MOCK_API_BASE_URL',           'http://192.168.100.10:8003')
MOCK_API_PRODUCTS_PATH      = os.getenv('MOCK_API_PRODUCTS_PATH',      '/api/v1/products/')
MOCK_API_SHOP_ID_HEADER     = os.getenv('MOCK_API_SHOP_ID_HEADER',     'X-Store-ID')

# Request timeouts (seconds)
EXTERNAL_REQUEST_TIMEOUT = int(os.getenv('EXTERNAL_REQUEST_TIMEOUT', '5'))
