 codex/update-django-settings-for-development
"""Django settings for the BioNexus project."""

from __future__ import annotations

from pathlib import Path
import os


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Core Django settings -------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS: list[str] = []


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

 codex/run-migrations-and-update-documentation
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dummy-secret-key"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
 main
    "rest_framework",
    "modules.samples",
    "modules.protocols",
]

 codex/update-django-settings-for-development
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "core.wsgi.application"


# Database configuration

 main
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

 codex/update-django-settings-for-development

# Django REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}


# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files
STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECRET_KEY = 'test-secret-key'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'modules.samples',
    'modules.protocols',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ROOT_URLCONF = 'core.urls'

MIDDLEWARE = []
 main
 main
