#!/usr/bin/env python
"""Django's command-line utility (manage.py).

Why it is needed:
    Every Django project has a manage.py file. You use it to run the development
    server, create database tables (migrations), create users, and run tests.

Examples (run these inside the project folder):
    python manage.py migrate
    python manage.py runserver
    python manage.py test
"""
import os
import sys


def main():
    """Tell Django which settings module to use, then run the requested command."""
    # DJANGO_SETTINGS_MODULE tells Django where our settings file lives.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Could not import Django. Is the virtual environment activated and "
            "have you run 'pip install -r requirements.txt'?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
