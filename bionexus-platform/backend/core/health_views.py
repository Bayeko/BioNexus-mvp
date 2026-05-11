"""Health-check endpoint for the Labionexus Platform.

Exposes ``GET /healthz`` for synthetic uptime monitoring (UptimeRobot,
GCP Cloud Monitoring, Sentry cron, etc.).

The endpoint checks three liveness signals :

1. **Database connectivity** : a trivial ``SELECT 1`` against the default
   connection. Catches connection pool exhaustion, network partitions,
   and Cloud SQL failovers.
2. **Audit trail freshness** : timestamp of the most recent
   :class:`core.models.AuditLog` row. Helps detect a stuck or detached
   signal pipeline (the audit chain MUST always be advancing in a live
   system). Returns ``null`` when no audit records exist yet, which is
   normal for fresh tenants.
3. **Persistence WAL state** : count of pending and failed
   :class:`modules.persistence.models.PendingMeasurement` rows. A growing
   ``failed`` count is the leading indicator that the sync engine has
   stalled even when the API itself is responsive.

The response shape stays stable so that probes can rely on it ::

    {
      "status": "ok" | "degraded" | "error",
      "version": "1.0.0",
      "timestamp": "<UTC ISO-8601>",
      "checks": {
        "database":          { "status": "ok" | "error", "latency_ms": <int> },
        "audit_trail":       { "status": "ok" | "warn", "last_write": "..." },
        "persistence_queue": { "status": "ok" | "warn", "pending": <int>, "failed": <int> }
      }
    }

HTTP status is 200 when ``status`` is ``ok``, 503 otherwise. UptimeRobot
treats anything non-2xx as down ; this gives operators a fast binary
signal plus a structured payload for diagnosis.

No authentication is required : the endpoint is safe to expose publicly
(it leaks no business data) and probes typically cannot authenticate.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Stable version string until release management lands. Bump alongside
# the Sentry release tag in CI so cross-system correlation works.
PLATFORM_VERSION = "1.0.0"


def _check_database() -> dict:
    """Verify the default database is reachable."""
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {"status": "ok", "latency_ms": elapsed_ms}
    except Exception as exc:  # pragma: no cover - connection errors are env-specific
        return {"status": "error", "error": str(exc)[:200]}


def _check_audit_trail() -> dict:
    """Report timestamp of the most recent AuditLog entry."""
    try:
        from core.models import AuditLog

        last = (
            AuditLog.objects.order_by("-timestamp", "-id")
            .values_list("timestamp", flat=True)
            .first()
        )
        if last is None:
            return {"status": "ok", "last_write": None}
        return {"status": "ok", "last_write": last.isoformat()}
    except Exception as exc:  # pragma: no cover
        return {"status": "warn", "error": str(exc)[:200]}


def _check_persistence_queue() -> dict:
    """Surface the sync engine queue health."""
    try:
        from modules.persistence.models import PendingMeasurement

        pending = PendingMeasurement.objects.filter(sync_status="pending").count()
        failed = PendingMeasurement.objects.filter(sync_status="failed").count()
        # Failed rows are not catastrophic alone (the sync engine retries),
        # but a non-zero failed count gets a 'warn' badge so operators
        # notice it during a routine probe.
        sub_status = "warn" if failed > 0 else "ok"
        return {"status": sub_status, "pending": pending, "failed": failed}
    except Exception as exc:  # pragma: no cover
        return {"status": "warn", "error": str(exc)[:200]}


@api_view(["GET"])
@permission_classes([AllowAny])
def healthz(request):
    """Return the platform health snapshot.

    Returns HTTP 200 with ``status: ok`` when all subsystems are healthy,
    HTTP 503 with ``status: degraded`` or ``status: error`` otherwise.
    """
    checks = {
        "database": _check_database(),
        "audit_trail": _check_audit_trail(),
        "persistence_queue": _check_persistence_queue(),
    }

    # Aggregate: any 'error' fails the probe, any 'warn' degrades it.
    sub_states = {c["status"] for c in checks.values()}
    if "error" in sub_states:
        overall = "error"
    elif "warn" in sub_states:
        overall = "degraded"
    else:
        overall = "ok"

    body = {
        "status": overall,
        "version": PLATFORM_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    http_status = 200 if overall == "ok" else 503
    return Response(body, status=http_status)
