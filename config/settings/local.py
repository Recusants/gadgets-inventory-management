"""
Local development settings for 21 Void Technologies.
Uses SQLite for zero-setup local deployment.
"""

from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-dev-secret-key-21void-tech-2026')

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# In-memory or local cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake-21void',
    }
}

# Ensure WhiteNoise reads directly from static/ during local development
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

