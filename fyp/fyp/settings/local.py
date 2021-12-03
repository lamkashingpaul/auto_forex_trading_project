from .base import *


SECRET_KEY = 'j9fz3e+x8$33zl79z#9xd7)(a)r)pg(df^i17vzoz1t0lrk7ia'

DEBUG = True

ALLOWED_HOSTS += ['127.0.0.1']

INSTALLED_APPS += [
    # Debug tools
    'debug_toolbar',
]

MIDDLEWARE += [
    # Debug tools
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# IPs for debug tool
INTERNAL_IPS += [
    '127.0.0.1',
]
