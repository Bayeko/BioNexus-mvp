"""In-process Django mock of Vault's OAuth2 endpoints.

The unified ``lims_mock_server`` (a standalone HTTP server on port 8001)
covers the REST API mocks. The OAuth2 flow, however, involves a browser
redirect back to the Labionexus frontend ; running it through the
standalone mock server would force the frontend to know two different
hosts.

To keep the OAuth demo path single-host, the mock endpoints below run
INSIDE the Django process under ``/mock-veeva/auth/oauth2/...``. Set
``VEEVA_BASE_URL=http://localhost:8000/mock-veeva`` (same Django host)
to drive the full OAuth2 flow without leaving the demo machine.

In production these routes return 404 unless explicitly enabled via
``VEEVA_MOCK_OAUTH_DJANGO=true`` so they never accidentally hand out
tokens to a stranger. The default in DEBUG dev is to enable them.
"""

from __future__ import annotations

import logging
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger("veeva.mock_oauth")


# Module-level stores for issued authorization codes + refresh tokens.
# Single-process demo only ; tests reset via reset_oauth_state().
_AUTH_CODES: dict[str, dict] = {}
_REFRESH_TOKENS: set[str] = set()


def reset_oauth_state() -> None:
    """Test helper : clear the in-memory OAuth code + refresh-token stores."""
    _AUTH_CODES.clear()
    _REFRESH_TOKENS.clear()


def _mock_enabled() -> bool:
    """The mock routes are active in DEBUG or when explicitly toggled on."""
    if getattr(settings, "DEBUG", False):
        return True
    import os
    return os.environ.get("VEEVA_MOCK_OAUTH_DJANGO", "false").lower() == "true"


@require_http_methods(["GET"])
def mock_authorize(request: HttpRequest) -> HttpResponse:
    """Mock of GET /auth/oauth2/authorize.

    Auto-approves the requested scope and redirects to the caller's
    ``redirect_uri`` with ``code`` + ``state``. A real Vault tenant
    would ask the user to log in and confirm scope first.
    """
    if not _mock_enabled():
        return HttpResponseNotFound()

    client_id = request.GET.get("client_id", "")
    redirect_uri = request.GET.get("redirect_uri", "")
    state = request.GET.get("state", "")
    response_type = request.GET.get("response_type", "")

    if response_type != "code" or not client_id or not redirect_uri:
        return JsonResponse(
            {
                "error": "invalid_request",
                "error_description": "Missing required OAuth parameter",
            },
            status=400,
        )

    code = uuid.uuid4().hex
    _AUTH_CODES[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    logger.info("[mock-veeva-oauth] code issued for client_id=%s", client_id)
    target = f"{redirect_uri}?{urlencode({'code': code, 'state': state})}"
    return HttpResponseRedirect(target)


@csrf_exempt
@require_http_methods(["POST"])
def mock_token(request: HttpRequest) -> JsonResponse:
    """Mock of POST /auth/oauth2/token.

    Handles both ``grant_type=authorization_code`` (initial swap) and
    ``grant_type=refresh_token`` (rotation). Returns the canonical
    OAuth 2.0 token response shape with a 1-hour expiry.
    """
    if not _mock_enabled():
        return JsonResponse({"error": "not_found"}, status=404)

    grant_type = request.POST.get("grant_type", "")

    if grant_type == "authorization_code":
        code = request.POST.get("code", "")
        client_id = request.POST.get("client_id", "")
        redirect_uri = request.POST.get("redirect_uri", "")
        entry = _AUTH_CODES.pop(code, None)
        if entry is None:
            return JsonResponse(
                {"error": "invalid_grant", "error_description": "Unknown or used code"},
                status=400,
            )
        if entry["client_id"] != client_id or entry["redirect_uri"] != redirect_uri:
            return JsonResponse(
                {"error": "invalid_grant", "error_description": "Client mismatch"},
                status=400,
            )

    elif grant_type == "refresh_token":
        refresh = request.POST.get("refresh_token", "")
        if refresh not in _REFRESH_TOKENS:
            return JsonResponse(
                {"error": "invalid_grant", "error_description": "Unknown refresh token"},
                status=400,
            )
        # One-time refresh tokens : retire the old one before issuing the new.
        _REFRESH_TOKENS.discard(refresh)

    else:
        return JsonResponse(
            {"error": "unsupported_grant_type", "error_description": grant_type},
            status=400,
        )

    access_token = f"vault-at-{uuid.uuid4().hex}"
    refresh_token = f"vault-rt-{uuid.uuid4().hex}"
    _REFRESH_TOKENS.add(refresh_token)

    return JsonResponse(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": request.POST.get("scope", "openid"),
        },
        status=200,
    )


@require_http_methods(["GET"])
def mock_userinfo(request: HttpRequest) -> JsonResponse:
    """Mock of GET /auth/oauth2/userinfo. Returns a static profile."""
    if not _mock_enabled():
        return JsonResponse({"error": "not_found"}, status=404)

    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return JsonResponse({"error": "invalid_token"}, status=401)
    return JsonResponse(
        {
            "sub": "mock-user-1",
            "email": "demo-user@labionexus.local",
            "name": "Demo User",
            "preferred_username": "demo-user",
        },
        status=200,
    )
