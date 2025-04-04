from .base import *

DEBUG = False
ALLOWED_HOSTS = ["139.59.166.206", "sophi-oxf.io", "www.sophi-oxf.io"]
MEDIA_ROOT = "/root/simulations"

# Security settings
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
