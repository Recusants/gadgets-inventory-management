"""
Local Environment Development settings with PostgreSQL for Gadget Store System.
Connects directly to PostgreSQL (local service or dev PostgreSQL container on localhost:5433)
from local virtualenv without requiring Docker for the Django web process.
"""

from .base import *

DEBUG = True

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or os.environ.get('SECRET_KEY', 'env-dev-secret-key-gadget-store')

ALLOWED_HOSTS = ['*']

db_name = os.environ.get('POSTGRES_DB') or os.environ.get('DB_NAME') or os.environ.get('DEV_DB_NAME', 'gadget_store_dev_db')
db_user = os.environ.get('POSTGRES_USER') or os.environ.get('DB_USER') or os.environ.get('DEV_DB_USER', 'gadget_dev_user')
db_password = os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DB_PASSWORD') or os.environ.get('DEV_DB_PASSWORD', 'dev_password')
db_host = os.environ.get('POSTGRES_HOST') or os.environ.get('DB_HOST', 'localhost')
db_port = os.environ.get('POSTGRES_PORT') or os.environ.get('DB_PORT') or os.environ.get('DEV_DB_PORT', '5433')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': db_host,
        'PORT': str(db_port),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'env-dev-cache-gadget-store',
    }
}

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
