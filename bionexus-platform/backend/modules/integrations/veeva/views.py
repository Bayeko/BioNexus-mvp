"""Veeva integration HTTP surface.

Read-only endpoints (powering Integrations.jsx + dedicated VeevaConnect):
  - GET  /api/integrations/veeva/status/      integration mode + counts
  - GET  /api/integrations/veeva/log/         push log list (filterable)

OAuth2 Authorization Code endpoints (only meaningful when
``VEEVA_AUTH_FLOW=oauth2``):
  - GET  /api/integrations/veeva/oauth/authorize-url/   start the flow
  - POST /api/integrations/veeva/oauth/callback/        complete the swap
  - GET  /api/integrations/veeva/oauth/status/          token status

Auth: same DRF defaults as the rest of /api/. The push log can contain
operator IDs (pseudonymized) and lot numbers (operational data), so it
is not public — sits behind the same JWT auth as everything else.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import oauth
from .models import IntegrationPushLog, VeevaOAuthToken
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


# ---------------------------------------------------------------------------
# OAuth2 endpoints (Authorization Code flow)
# ---------------------------------------------------------------------------

@api_view(["GET"])
def oauth_authorize_url(request):
    """Return the URL the operator should browse to begin OAuth2.

    Side effect : mints a fresh CSRF state token and persists it on
    the singleton :class:`VeevaOAuthToken` row. The token is round-
    tripped through Vault and validated when the callback comes back.
    """
    if not oauth.is_oauth2_enabled():
        return Response(
            {"detail": "VEEVA_AUTH_FLOW is not set to oauth2."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        url = oauth.build_authorize_url()
    except oauth.VeevaOAuthError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"authorize_url": url})


@api_view(["POST"])
def oauth_callback(request):
    """Complete the OAuth2 flow by exchanging the code for tokens.

    Body : ``{"code": "<vault-code>", "state": "<round-tripped-state>"}``
    The frontend strips both parameters off the redirect_uri landing
    page and POSTs them here.
    """
    if not oauth.is_oauth2_enabled():
        return Response(
            {"detail": "VEEVA_AUTH_FLOW is not set to oauth2."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = request.data.get("code")
    state = request.data.get("state")
    if not code or not state:
        return Response(
            {"detail": "code and state are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        oauth.exchange_code_for_tokens(code, state)
    except oauth.VeevaOAuthError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    record = VeevaOAuthToken.objects.get(pk=1)
    return Response(
        {
            "success": True,
            "access_token_expires_at": record.token_expires_at,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def oauth_status(request):
    """Report whether OAuth2 is configured and whether a token is cached.

    Used by the frontend to decide between "Connect via OAuth2" (no
    token) and "Re-authorize" (token cached). Never exposes the token
    itself.
    """
    enabled = oauth.is_oauth2_enabled()
    try:
        record = VeevaOAuthToken.objects.get(pk=1)
        has_token = bool(record.access_token_enc) and bool(record.token_expires_at)
        expires_at = record.token_expires_at
    except VeevaOAuthToken.DoesNotExist:
        has_token = False
        expires_at = None
    return Response(
        {
            "oauth2_enabled": enabled,
            "has_active_token": has_token,
            "token_expires_at": expires_at,
        }
    )
