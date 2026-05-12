"""Read-only Veeva integration status + push log endpoints.

These power the Integrations.jsx "Veeva Vault" card. Both endpoints are
intentionally GET-only and read-only: the integration is driven from
signals + the mock server, not from the API surface.

Auth: same DRF defaults as the rest of /api/. The push log can contain
operator IDs (pseudonymized) and lot numbers (operational data), so it's
not public — sits behind the same JWT auth as everything else.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import IntegrationPushLog
from .serializers import IntegrationPushLogSerializer


class VeevaPushLogViewSet(viewsets.ReadOnlyModelViewSet):
    """List + retrieve push log entries (newest first).

    Despite the URL prefix, this endpoint serves every LIMS vendor's
    push log — they all share the IntegrationPushLog table. Filter
    with ``?vendor=<empower|labware|starlims|benchling|veeva>``.

    GET /api/integrations/veeva/log/                    — all vendors
    GET /api/integrations/veeva/log/?vendor=empower     — Empower only
    GET /api/integrations/veeva/log/<id>/               — single entry
    """

    serializer_class = IntegrationPushLogSerializer

    def get_queryset(self):
        qs = IntegrationPushLog.objects.all().order_by("-created_at")
        vendor = self.request.query_params.get("vendor")
        if vendor:
            qs = qs.filter(vendor=vendor.lower())
        return qs


_VENDOR_SETTINGS_PREFIX = {
    "veeva": "VEEVA",
    "empower": "EMPOWER",
    "labware": "LABWARE",
    "starlims": "STARLIMS",
    "benchling": "BENCHLING",
}


@api_view(["GET"])
def veeva_status(request):
    """Return current integration mode + summary counts.

    Although the URL says "veeva", this endpoint serves every LIMS
    vendor — filter with ``?vendor=<name>`` to scope the response to a
    specific connector. Without ``vendor``, the response describes
    Veeva (the default home of this endpoint, kept for backward compat).
    """
    requested_vendor = (request.query_params.get("vendor") or "veeva").lower()
    prefix = _VENDOR_SETTINGS_PREFIX.get(requested_vendor, "VEEVA")

    mode = str(getattr(settings, f"{prefix}_MODE", "disabled")).lower()
    enabled = bool(getattr(settings, f"{prefix}_INTEGRATION_ENABLED", False))
    base_url = getattr(settings, f"{prefix}_BASE_URL", "")

    qs = IntegrationPushLog.objects.filter(vendor=requested_vendor)
    counts = {
        "total": qs.count(),
        "success": qs.filter(status=IntegrationPushLog.STATUS_SUCCESS).count(),
        "failed": qs.filter(status=IntegrationPushLog.STATUS_FAILED).count(),
        "dead_letter": qs.filter(status=IntegrationPushLog.STATUS_DEAD_LETTER).count(),
        "in_flight": qs.filter(status=IntegrationPushLog.STATUS_IN_FLIGHT).count(),
        "pending": qs.filter(status=IntegrationPushLog.STATUS_PENDING).count(),
    }

    return Response(
        {
            "vendor": requested_vendor,
            "mode": mode,
            "enabled": enabled,
            "base_url": base_url if mode != "prod" else "<redacted>",
            "counts": counts,
            "label": _badge_label(mode, enabled),
        },
        status=status.HTTP_200_OK,
    )


def _badge_label(mode: str, enabled: bool) -> str:
    if not enabled or mode == "disabled":
        return "DISABLED"
    if mode == "mock":
        return "MOCK MODE - not connected to real Vault"
    if mode == "sandbox":
        return "SANDBOX - non-production Vault tenant"
    if mode == "prod":
        return "PRODUCTION"
    return "UNKNOWN"
