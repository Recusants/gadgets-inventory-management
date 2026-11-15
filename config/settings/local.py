"""
Local development settings for Gadget Store System.
Uses SQLite (db.sqlite3) for zero-setup local deployment and testing.
"""

from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or os.environ.get('SECRET_KEY', 'local-dev-secret-key-gadget-store-2026')

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'local-sqlite-cache-gadget-store',
    }
}

# Ensure WhiteNoise reads directly from static/ during local development
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
