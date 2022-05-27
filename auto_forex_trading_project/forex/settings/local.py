from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'j9fz3e+x8$33zl79z#9xd7)(a)r)pg(df^i17vzoz1t0lrk7ia'  # dummy secret key used for development purposes

DEBUG = True

ALLOWED_HOSTS += ['127.0.0.1']

INSTALLED_APPS += [
    'django.contrib.admin',  # admin apps
    'debug_toolbar',  # debug tools
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  # debug tools
]

# allowed IPs for debug context
INTERNAL_IPS += [
    '127.0.0.1',
]
