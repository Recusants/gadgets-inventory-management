"""
Docker development settings for 21 Void Technologies.
Uses PostgreSQL 16 container with live reload.
"""

from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'docker-dev-secret-key-21void-tech')

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'twentyone_void_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'docker-dev-cache-21void',
    }
}
