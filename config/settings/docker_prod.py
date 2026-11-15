"""
Docker production settings for Gadget Store System.
Production hardening, PostgreSQL 16, Gunicorn + WhiteNoise.
"""

from .base import *

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'prod-fallback-secret-key-gadget-store-2026'

allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
if allowed_hosts_env == '*' or '*' in [h.strip() for h in allowed_hosts_env.split(',')]:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8086,http://localhost:8086')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_env.split(',') if origin.strip()]

db_name = os.environ.get('POSTGRES_DB') or os.environ.get('DB_NAME', 'twentyone_void_prod_db')
db_user = os.environ.get('POSTGRES_USER') or os.environ.get('DB_USER', 'twentyone_user')
db_password = os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DB_PASSWORD', '')
db_host = os.environ.get('POSTGRES_HOST') or os.environ.get('DB_HOST', 'db')
db_port = os.environ.get('POSTGRES_PORT') or os.environ.get('DB_PORT', '5432')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': db_host,
        'PORT': db_port,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'docker-prod-cache-gadget-store',
    }
}

# Production Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# Static files optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_MANIFEST_STRICT = False
