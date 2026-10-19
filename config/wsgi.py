"""WSGI entry point.

Why it is needed:
    WSGI is the standard way Python web servers talk to Django. For this local
    academic project you normally use 'python manage.py runserver' instead.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
