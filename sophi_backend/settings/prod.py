from .base import *

DEBUG = False
ALLOWED_HOSTS = ["139.59.166.206", "sophi-oxf.io", "www.sophi-oxf.io", "api.sophi-oxf.io"]
MEDIA_ROOT = "/root/sophi-data"

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "https://sophi-oxf.io",
]

CSRF_TRUSTED_ORIGINS = [
    "https://sophi-oxf.io",
]
# Security settings
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
