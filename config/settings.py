"""Django settings for the Blockchain-Based Digital Evidence Chain of Custody System.

This is a LOCAL ACADEMIC DEMONSTRATION configuration.
Do not deploy it to the internet as-is: DEBUG is on by default, the secret key is a
development key, and SQLite + local file storage are not high-assurance evidence storage.

Settings can be overridden with environment variables (see README.md):
    DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS
"""
import os
from pathlib import Path

# BASE_DIR is the project root folder (the folder that contains manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent


def _env_flag(name, default):
    """Read a True/False value from an environment variable.

    Inputs: the variable name and a default (bool) used when it is not set.
    Returns: True or False.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Security basics
# ---------------------------------------------------------------------------
# SECRET_KEY signs sessions and CSRF tokens. The fallback value below is ONLY for
# local development; it is clearly labelled insecure. Set DJANGO_SECRET_KEY in a
# real environment so no real secret is ever stored in source code.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-development-key-do-not-use-in-production",
)

DEBUG = _env_flag("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",          # built-in users, passwords (hashed), login
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Our own apps:
    "evidence.apps.EvidenceConfig",          # cases, evidence, custody events
    "blockchain.apps.BlockchainConfig",      # block records + chain logic
    "verification.apps.VerificationConfig",  # evidence integrity verification
    "reports.apps.ReportsConfig",            # PDF report generation
]

# Middleware = small steps every request passes through. CsrfViewMiddleware keeps
# CSRF protection enabled for every POST form.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database: SQLite (a single file called db.sqlite3 in the project folder)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Passwords and login
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# Time zones
# ---------------------------------------------------------------------------
# Django STORES every timestamp in the database in UTC (USE_TZ = True). That gives
# an unambiguous, comparable time no matter where the server is.
# When a template or the PDF report DISPLAYS a timestamp, Django converts it to
# TIME_ZONE below, so people see their local time. Change TIME_ZONE if needed
# (for example "UTC"). Blockchain blocks always use the UTC ISO-8601 string.
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"
LANGUAGE_CODE = "en-us"
USE_I18N = False
DATETIME_FORMAT = "d M Y, H:i:s"
DATE_FORMAT = "d M Y"

# ---------------------------------------------------------------------------
# Static files (CSS / JS / vendored Bootstrap)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ---------------------------------------------------------------------------
# Evidence file storage (PRIVATE)
# ---------------------------------------------------------------------------
# Uploaded evidence is stored in this folder. There is deliberately NO MEDIA_URL and
# NO URL route serving this folder, so evidence files are never exposed publicly.
EVIDENCE_STORAGE_ROOT = BASE_DIR / "private_evidence"

# Maximum upload size in bytes (default 50 MB). Change it here if needed.
MAX_EVIDENCE_UPLOAD_BYTES = 50 * 1024 * 1024

# Only these file extensions may be registered as evidence. Executable and script
# types (exe, bat, ps1, js, ...) are intentionally NOT in the list.
ALLOWED_EVIDENCE_EXTENSIONS = [
    "txt", "log", "csv", "json", "xml", "md", "eml",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp",
    "mp3", "wav", "mp4", "avi", "mov", "mkv",
    "zip", "pcap", "pcapng", "img", "dd", "bin",
]

# How many bytes to read at a time when hashing a file (1 MiB).
HASH_CHUNK_SIZE = 1024 * 1024

# Django keeps uploads above this size on disk instead of in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
# Limit for non-file form data only (file uploads are limited by our own check).
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
