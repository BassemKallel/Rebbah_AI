import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tiktak-ai-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
# Ensure production domains are always allowed statically
for host in ['ai2.tiktakpro.com']:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)



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
        'apps.crm.services.authentication.JWTCompanyAuthentication',
        'apps.crm.services.authentication.StaticTokenAuthentication',
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

_REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
_REDIS_AUTH = f":{_REDIS_PASSWORD}@" if _REDIS_PASSWORD else ""

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{_REDIS_AUTH}{os.getenv("REDIS_HOST", "redis")}:{os.getenv("REDIS_PORT", "6379")}/1',
    }
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3010",
    "https://ai2.tiktakpro.com"
]

# Allow all ngrok subdomains for local development
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.ngrok-free\.app$",
    r"^https://.*\.ngrok-free\.dev$",
    r"^https://.*\.ngrok\.io$",
]


# Trusted origins for CSRF — must include all domains that POST to Django
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'https://ai2.tiktakpro.com'
    ).split(',')
    if origin.strip()
]
# Ensure production domains are always allowed in CSRF trusted origins
for origin in ['https://ai2.tiktakpro.com']:
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Allow ngrok for local development — Meta webhook can POST from ngrok URLs
_ngrok_host = os.getenv('NGROK_URL', '')  # e.g. https://xxxx.ngrok-free.app
if _ngrok_host and _ngrok_host not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_ngrok_host)

# ======= External Services =======
# Gemini LLM Direct Mode

# Vision Service (CLIP + pgvector)
VISION_SERVICE_URL   = os.getenv('VISION_SERVICE_URL',   'http://vision-service:8002')
VISION_SEARCH_PATH   = os.getenv('VISION_SEARCH_PATH',   '/search-similar')

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

# ============================================================
# CELERY CONFIGURATION (Async Task Queue — Redis Broker)
# ============================================================
# Points to the same Redis container already used for hot memory
# and the sliding-window debouncer. Uses db=2 to avoid collisions.
_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = os.getenv("REDIS_PORT", "6379")

CELERY_BROKER_URL         = f"redis://{_REDIS_AUTH}{_REDIS_HOST}:{_REDIS_PORT}/2"
CELERY_RESULT_BACKEND     = f"redis://{_REDIS_AUTH}{_REDIS_HOST}:{_REDIS_PORT}/2"
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
# Result expiration: 1 hour (matching hot-memory TTL)
CELERY_RESULT_EXPIRES     = 3600

