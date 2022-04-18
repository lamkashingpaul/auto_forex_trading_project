"""
WSGI config for forex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ['DJANGO_SETTINGS_MODULE'] = 'forex.settings.production'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forex.settings.production')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
