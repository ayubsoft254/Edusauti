from .base import *

# Development-specific settings
DEBUG = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allauth email verification for development
ACCOUNT_EMAIL_VERIFICATION = 'optional'

# CORS settings for development (if needed)
CORS_ALLOW_ALL_ORIGINS = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'users': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

# Channel layers for development
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}