from .base import *

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS += ['lamkashingpaul.com']

WSGI_APPLICATION = 'forex.wsgi.application'
