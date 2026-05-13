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
    "drf_spectacular",
    "core",  # Must come before django.contrib.admin (uses custom AUTH_USER_MODEL)
    "django.contrib.admin",
    "modules.instruments",
    "modules.samples",
    "modules.measurements",
    "modules.protocols",
    "modules.persistence",
    "modules.integrations.veeva",
    "modules.integrations.lims_connectors",
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
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BioNexus API",
    "DESCRIPTION": "Laboratory data integration platform — REST API for instruments, samples, measurements, audit trail, exports, and webhooks.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "Instruments", "description": "Laboratory instrument registration and monitoring"},
        {"name": "Samples", "description": "Sample tracking and lifecycle management"},
        {"name": "Measurements", "description": "Measurement data capture with SHA-256 integrity"},
        {"name": "Audit Trail", "description": "Immutable audit log — 21 CFR Part 11 compliant"},
        {"name": "Export", "description": "CSV/PDF export for LIMS integration"},
        {"name": "Webhooks", "description": "Event notifications for external systems"},
        {"name": "Smart Parser", "description": "CSV file parsing and instrument detection"},
    ],
}


# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files
STATIC_URL = "static/"


# ---------------------------------------------------------------------------
# Celery / async task queue
# ---------------------------------------------------------------------------
# In production set CELERY_BROKER_URL to a Redis instance (e.g.
# redis://localhost:6379/0). In dev and tests CELERY_TASK_ALWAYS_EAGER
# defaults to True so tasks run inline and no broker is required.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0",
)
CELERY_TASK_ALWAYS_EAGER = os.environ.get(
    "CELERY_TASK_ALWAYS_EAGER", "true",
).lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TIME_LIMIT = 600       # hard 10-min timeout per task
CELERY_TASK_SOFT_TIME_LIMIT = 540  # soft 9-min for graceful cleanup
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "retry-failed-veeva-pushes": {
        "task": "modules.integrations.veeva.tasks.retry_failed_pushes",
        "schedule": 300.0,  # every 5 minutes when `celery beat` is running
    },
}


# ---------------------------------------------------------------------------
# Veeva Vault integration (LBN-INT-VEEVA-001)
# ---------------------------------------------------------------------------
# VEEVA_MODE pickin order: disabled (default, prod-safe) | mock | sandbox | prod.
# "disabled" guarantees no outbound network calls regardless of any other
# setting, so a misconfigured prod won't accidentally fire pushes.
VEEVA_MODE = os.environ.get("VEEVA_MODE", "disabled")
VEEVA_INTEGRATION_ENABLED = (
    os.environ.get("VEEVA_INTEGRATION_ENABLED", "false").lower() == "true"
)
VEEVA_BASE_URL = os.environ.get("VEEVA_BASE_URL", "")
VEEVA_SHARED_SECRET = os.environ.get("VEEVA_SHARED_SECRET", "")
# Production guard: prod mode also requires VEEVA_PROD_CONFIRMED=true (read
# directly from os.environ in client.py — kept out of settings so the prod
# guard can't be bypassed via a Django settings override in tests).


# ---------------------------------------------------------------------------
# LIMS / ELN / CDS connectors (modules.integrations.lims_connectors)
# ---------------------------------------------------------------------------
# Each vendor follows the same env-var pattern:
#   <VENDOR>_MODE                  : disabled (default) | mock | sandbox | prod
#   <VENDOR>_INTEGRATION_ENABLED   : "true" to wire post_save(Measurement)
#   <VENDOR>_BASE_URL              : target host (mock: http://localhost:8001)
#   <VENDOR>_SHARED_SECRET         : HMAC signing secret
#   <VENDOR>_PROD_CONFIRMED        : env-only "true" to allow prod mode
# Authentication tokens are vendor-specific and read directly from
# os.environ inside each client's _auth_headers().

# Waters Empower Web API
EMPOWER_MODE = os.environ.get("EMPOWER_MODE", "disabled")
EMPOWER_INTEGRATION_ENABLED = (
    os.environ.get("EMPOWER_INTEGRATION_ENABLED", "false").lower() == "true"
)
EMPOWER_BASE_URL = os.environ.get("EMPOWER_BASE_URL", "")
EMPOWER_SHARED_SECRET = os.environ.get("EMPOWER_SHARED_SECRET", "")

# LabWare LIMS
LABWARE_MODE = os.environ.get("LABWARE_MODE", "disabled")
LABWARE_INTEGRATION_ENABLED = (
    os.environ.get("LABWARE_INTEGRATION_ENABLED", "false").lower() == "true"
)
LABWARE_BASE_URL = os.environ.get("LABWARE_BASE_URL", "")
LABWARE_SHARED_SECRET = os.environ.get("LABWARE_SHARED_SECRET", "")

# STARLIMS
STARLIMS_MODE = os.environ.get("STARLIMS_MODE", "disabled")
STARLIMS_INTEGRATION_ENABLED = (
    os.environ.get("STARLIMS_INTEGRATION_ENABLED", "false").lower() == "true"
)
STARLIMS_BASE_URL = os.environ.get("STARLIMS_BASE_URL", "")
STARLIMS_SHARED_SECRET = os.environ.get("STARLIMS_SHARED_SECRET", "")

# Benchling ELN
BENCHLING_MODE = os.environ.get("BENCHLING_MODE", "disabled")
BENCHLING_INTEGRATION_ENABLED = (
    os.environ.get("BENCHLING_INTEGRATION_ENABLED", "false").lower() == "true"
)
BENCHLING_BASE_URL = os.environ.get("BENCHLING_BASE_URL", "")
BENCHLING_SHARED_SECRET = os.environ.get("BENCHLING_SHARED_SECRET", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Observability (Sentry) -------------------------------------------------
#
# Initialized only when SENTRY_DSN is present so dev / CI / unit tests stay
# free of network calls and side effects. Severity tags (p0..p3) drive the
# alert rules configured in the Sentry web UI per the incident response
# runbook. The release tag is set from CI (commit SHA) so post-mortems can
# correlate errors with deploys.

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "dev")
SENTRY_RELEASE = os.environ.get("SENTRY_RELEASE", "")
# Traces sampling: keep low in prod to stay within free-plan quota.
# Override via env when investigating a latency regression.
SENTRY_TRACES_SAMPLE_RATE = float(
    os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
)

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE or None,
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,  # No PII policy: never auto-attach user info
        )
        # Default severity tag for un-tagged errors. Handlers that know
        # their severity (capture_message(..., level=...)) override this.
        sentry_sdk.set_tag("severity", "p2")
    except ImportError:  # pragma: no cover - SDK is optional at runtime
        pass


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

