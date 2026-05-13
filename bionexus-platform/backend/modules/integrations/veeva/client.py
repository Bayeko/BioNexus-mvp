"""Veeva-specific clients on top of the shared ``base.client`` primitives.

Veeva keeps its own naming (``push_quality_event``, ``push_document``)
for clarity in the codebase and to preserve all existing tests. The
shared logic — HTTP, retries, signing, transport-error handling — lives
in ``modules/integrations/base/client.py``.
"""

from __future__ import annotations

import logging
import os

from modules.integrations.base.client import (
    BaseLimsClient,
    DisabledLimsClient,
    HttpLimsClient,
    PushResult,
)

log = logging.getLogger("veeva.client")


# ---------------------------------------------------------------------------
# Public types — re-exported so existing imports keep working.
# ---------------------------------------------------------------------------

class VeevaClient(BaseLimsClient):
    """Marker interface — narrowing :class:`BaseLimsClient` to Veeva's
    quality-event + document push surface.
    """

    vendor = "veeva"

    def push_quality_event(self, payload: dict) -> PushResult:
        """Veeva-named alias for ``push_object``."""
        return self.push_object(payload)


class DisabledVeevaClient(DisabledLimsClient, VeevaClient):
    """No-op Veeva client (used when ``VEEVA_MODE=disabled``)."""

    def __init__(self) -> None:
        super().__init__(vendor="VEEVA")


class HttpVeevaClient(HttpLimsClient, VeevaClient):
    """HTTP Veeva client base — Veeva REST v23.1 endpoint paths."""

    object_path = "/api/v23.1/vobjects/quality_event__v"
    document_path = "/api/v23.1/objects/documents"
    AUTH_PATH = "/api/v23.1/auth"
    # Backward-compat aliases used by older tests / docs.
    QUALITY_EVENT_PATH = object_path
    DOCUMENT_PATH = document_path


class MockVeevaClient(HttpVeevaClient):
    """Push against a local mock Vault (``VEEVA_MODE=mock``)."""

    def __init__(self, base_url: str, shared_secret: str, timeout_s: float = 10.0) -> None:
        super().__init__(
            base_url=base_url,
            shared_secret=shared_secret,
            timeout_s=timeout_s,
            mode="mock",
        )


class SandboxVeevaClient(HttpVeevaClient):
    """Push against a Veeva sandbox tenant."""

    def __init__(self, base_url: str, shared_secret: str, timeout_s: float = 10.0) -> None:
        super().__init__(
            base_url=base_url,
            shared_secret=shared_secret,
            timeout_s=timeout_s,
            mode="sandbox",
        )

    def _auth_headers(self) -> dict:
        """Return the Authorization header for outbound calls.

        Two auth flows are supported, dispatched on the
        ``VEEVA_AUTH_FLOW`` env var :

        - ``session_id`` (default) : ``VEEVA_SESSION_TOKEN`` env var
          supplies a Bearer token. Matches the v1 spec and the rest of
          the LIMS suite.
        - ``oauth2`` : the access token is fetched from the
          :class:`VeevaOAuthToken` singleton and refreshed transparently
          via ``oauth.get_or_refresh_access_token``. Requires the
          operator to have completed the Authorization Code flow once.
        """
        headers = super()._auth_headers()
        auth_flow = os.environ.get("VEEVA_AUTH_FLOW", "session_id").lower()

        if auth_flow == "oauth2":
            # Local import so the OAuth module + cryptography only load
            # when actually needed (keeps Session-ID-only deployments
            # free of the cryptography dependency at import time).
            try:
                from . import oauth as veeva_oauth

                token = veeva_oauth.get_or_refresh_access_token()
            except Exception as exc:  # noqa: BLE001 — explicit fallback
                log.warning(
                    "Veeva OAuth2 auth header lookup failed: %s ; falling "
                    "back to Session-ID env token (likely empty).",
                    exc,
                )
                token = ""
        else:
            token = os.environ.get("VEEVA_SESSION_TOKEN", "")

        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


class ProdVeevaClient(SandboxVeevaClient):
    """Production Vault tenant — gated by ``VEEVA_PROD_CONFIRMED=true``."""

    def __init__(self, base_url: str, shared_secret: str, timeout_s: float = 10.0) -> None:
        # Re-init via grandparent so mode reads "prod" not "sandbox".
        HttpVeevaClient.__init__(
            self,
            base_url=base_url,
            shared_secret=shared_secret,
            timeout_s=timeout_s,
            mode="prod",
        )


# ---------------------------------------------------------------------------
# Factory — kept on this module for backward compat with existing imports.
# ---------------------------------------------------------------------------

def build_client_from_settings() -> VeevaClient:
    """Pick the right Veeva client based on Django settings + env."""
    from django.conf import settings

    mode = str(getattr(settings, "VEEVA_MODE", "disabled")).lower()
    base_url = getattr(settings, "VEEVA_BASE_URL", "")
    secret = getattr(settings, "VEEVA_SHARED_SECRET", "")

    if mode == "disabled":
        return DisabledVeevaClient()
    if not base_url:
        log.warning(
            "VEEVA_MODE=%s but VEEVA_BASE_URL is empty - falling back to disabled.",
            mode,
        )
        return DisabledVeevaClient()
    if not secret:
        log.warning(
            "VEEVA_MODE=%s but VEEVA_SHARED_SECRET is empty - falling back to disabled.",
            mode,
        )
        return DisabledVeevaClient()
    if mode == "mock":
        return MockVeevaClient(base_url=base_url, shared_secret=secret)
    if mode == "sandbox":
        return SandboxVeevaClient(base_url=base_url, shared_secret=secret)
    if mode == "prod":
        if os.environ.get("VEEVA_PROD_CONFIRMED", "").lower() != "true":
            log.error(
                "VEEVA_MODE=prod requires VEEVA_PROD_CONFIRMED=true. "
                "Refusing to build a production client by accident."
            )
            return DisabledVeevaClient()
        return ProdVeevaClient(base_url=base_url, shared_secret=secret)

    log.warning("Unknown VEEVA_MODE=%r - falling back to disabled.", mode)
    return DisabledVeevaClient()
