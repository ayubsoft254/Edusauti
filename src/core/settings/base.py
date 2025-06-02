import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
]

LOCAL_APPS = [
    'users',
    'documents',
    'ai_services',
    'realtime',    
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/hour'
    }
}

# Allauth Configuration
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Allauth settings (Updated for new version)
ACCOUNT_LOGIN_METHODS = ['email', 'username']
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[EduSauti]"
ACCOUNT_EMAIL_CONFIRM_EXPIRE_DAYS = 3
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',  # 5 attempts per 5 minutes
}
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/dashboard/'

# Email confirmation settings
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/login/'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/dashboard/'

# Password settings
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_PASSWORD_INPUT_TYPE = 'password'

# Social account settings (optional - for future use)
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True

# Forms
ACCOUNT_FORMS = {
    'signup': 'users.forms.CustomSignupForm',
    'login': 'users.forms.CustomLoginForm',
}

# Azure Services Configuration
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = config('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', default='')
AZURE_DOCUMENT_INTELLIGENCE_KEY = config('AZURE_DOCUMENT_INTELLIGENCE_KEY', default='')
AZURE_OPENAI_ENDPOINT = config('AZURE_OPENAI_ENDPOINT', default='')
AZURE_OPENAI_KEY = config('AZURE_OPENAI_KEY', default='')
AZURE_OPENAI_API_VERSION = config('AZURE_OPENAI_API_VERSION', default='2024-02-15-preview')
AZURE_SPEECH_KEY = config('AZURE_SPEECH_KEY', default='')
AZURE_SPEECH_REGION = config('AZURE_SPEECH_REGION', default='')

# Redis Configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Email Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", cast=str, default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", cast=str, default="587") 
EMAIL_HOST_USER = config("EMAIL_HOST_USER", cast=str, default=None)
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", cast=str, default=None)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True) 
EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool, default=False)  
ADMIN_USER_NAME=config("ADMIN_USER_NAME", default="Admin user")
ADMIN_USER_EMAIL=config("ADMIN_USER_EMAIL", default=None)

MANAGERS=[]
ADMINS=[]
if all([ADMIN_USER_NAME, ADMIN_USER_EMAIL]):
    # 500 errors are emailed to these users
    ADMINS +=[
        (f'{ADMIN_USER_NAME}', f'{ADMIN_USER_EMAIL}')
    ]
    MANAGERS=ADMINS


# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME', default='')
AZURE_STORAGE_ACCOUNT_KEY = config('AZURE_STORAGE_ACCOUNT_KEY', default='')
AZURE_STORAGE_CONTAINER_NAME = config('AZURE_STORAGE_CONTAINER_NAME', default='edusauti-files')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Africa/Nairobi'

# Celery beat schedule for periodic tasks
CELERY_BEAT_SCHEDULE = {
    'cleanup-failed-documents': {
        'task': 'documents.tasks.cleanup_failed_documents',
        'schedule': 3600.0,  # Run every hour
    },
    'cleanup-old-files': {
        'task': 'documents.tasks.cleanup_old_files',
        'schedule': 86400.0,  # Run daily
    },
    'generate-usage-analytics': {
        'task': 'documents.tasks.generate_usage_analytics',
        'schedule': 43200.0,  # Run twice daily
    },
}