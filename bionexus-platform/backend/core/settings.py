import os
from pathlib import Path

"""Django settings for the BioNexus project."""

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Core Django settings -------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

_allowed_hosts = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
)
ALLOWED_HOSTS = [host for host in _allowed_hosts.split(",") if host]


# --- Authentication -------------------------------------------------------

# Use custom User model with tenant isolation
AUTH_USER_MODEL = "core.User"

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_LIFETIME = 15  # minutes
JWT_REFRESH_TOKEN_LIFETIME = 7  # days


# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "core",  # Must come before django.contrib.admin (uses custom AUTH_USER_MODEL)
    "django.contrib.admin",
    "modules.instruments",
    "modules.samples",
    "modules.measurements",
    "modules.protocols",
    "modules.persistence",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuditMiddleware",
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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    try:
        import dj_database_url  # type: ignore
    except Exception:  # pragma: no cover - dependency optional
        pass
    else:
        DATABASES["default"] = dj_database_url.parse(DATABASE_URL)


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


# --- Persistence / WAL Sync Engine ------------------------------------------

PERSISTENCE = {
    "BATCH_SIZE": 50,
    "BATCH_DELAY_MS": 500,
    "MAX_BURST_PER_MINUTE": 200,
    "BACKOFF_BASE_S": 1.0,
    "BACKOFF_MAX_S": 300.0,
    "BACKOFF_JITTER_S": 0.5,
    "CLOCK_DRIFT_THRESHOLD_MS": 5000,
    "SERVER_SLOW_MS": 2000,
    "SERVER_FAST_MS": 500,
}

