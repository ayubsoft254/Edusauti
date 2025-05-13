from config.settings import *
import os

# Security settings
DEBUG = False
ALLOWED_HOSTS = ['eduSauti-app.azurewebsites.net']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['POSTGRES_DB'],
        'USER': os.environ['POSTGRES_USER'],
        'PASSWORD': os.environ['POSTGRES_PASSWORD'],
        'HOST': os.environ['POSTGRES_HOST'],
        'PORT': '5432',
    }
}

# Static files
STATIC_ROOT = '/home/site/wwwroot/static'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Azure Blob Storage for media files
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = os.environ['AZURE_STORAGE_ACCOUNT']
AZURE_ACCOUNT_KEY = os.environ['AZURE_STORAGE_KEY']
AZURE_CONTAINER = 'documents'

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True