"""Veeva Vault OAuth2 Authorization Code flow.

Adds OAuth2 as an alternative authentication scheme to the existing
Session-ID + HMAC setup. Switching between the two is driven by the
``VEEVA_AUTH_FLOW`` env var:

    VEEVA_AUTH_FLOW=session_id   (default, env-driven Session-ID + HMAC)
    VEEVA_AUTH_FLOW=oauth2       (Authorization Code, this module)

Why both : Session-ID is the canonical Vault server-to-server pattern
and stays the production-safe default. OAuth2 lets the connector act
on behalf of a Vault user (rather than a service account), which is
required by some customers' security policies.

Flow (RFC 6749 §4.1) ::

    1. Operator clicks "Connect via OAuth2" in the admin UI.
    2. Backend builds an authorize URL with a CSRF ``state`` token and
       stashes the state in :class:`VeevaOAuthToken` (singleton row).
    3. Operator redirects to Vault, logs in, approves the scope.
    4. Vault redirects to ``VEEVA_OAUTH_REDIRECT_URI`` with ``code`` +
       ``state`` query parameters.
    5. Frontend POSTs both to /api/integrations/veeva/oauth/callback/.
       Backend verifies the state then exchanges the code for an
       ``access_token`` + ``refresh_token`` via Vault's token endpoint.
    6. Tokens are Fernet-encrypted and persisted on the singleton.
    7. Subsequent push calls fetch the access_token via
       :func:`get_or_refresh_access_token` and pass it as
       ``Authorization: Bearer <token>``.

Vault OAuth2 endpoint paths (REST API v23.1) ::

    Authorize :  ``<vault_url>/auth/oauth2/authorize``
    Token     :  ``<vault_url>/auth/oauth2/token``
    UserInfo  :  ``<vault_url>/auth/oauth2/userinfo``

For testing without a Vault sandbox we mock all three (see
:mod:`modules.integrations.veeva.mock_routes`).
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from core import encryption as core_encryption

if TYPE_CHECKING:
    from .models import VeevaOAuthToken

logger = logging.getLogger("veeva.oauth")

# Vault OAuth2 paths
OAUTH_AUTHORIZE_PATH = "/auth/oauth2/authorize"
OAUTH_TOKEN_PATH = "/auth/oauth2/token"
OAUTH_USERINFO_PATH = "/auth/oauth2/userinfo"

# Vault access tokens live ~1 hour. We refresh 5 minutes before expiry.
TOKEN_REFRESH_BUFFER_MINUTES = 5

# CSRF state TTL : 10 minutes is generous for a manual auth flow.
STATE_TTL_MINUTES = 10

# Default OAuth scope.
DEFAULT_SCOPE = "openid"


class VeevaOAuthError(RuntimeError):
    """Raised when OAuth flow fails (CSRF mismatch, exchange or refresh)."""


# ---------------------------------------------------------------------------
# Symmetric encryption — delegated to the pluggable core.encryption module
# ---------------------------------------------------------------------------
#
# Veeva OAuth credentials at rest are encrypted via ``core.encryption``,
# which exposes 3 backends (secret_key default, env_key, gcp_kms stub).
# Switch with the ``ENCRYPTION_PROVIDER`` env var. See
# ``core/encryption.py`` for the full activation procedure.
#
# We keep thin local wrappers so existing call sites + tests don't have
# to import core.encryption directly, and so a decrypt failure surfaces
# as the Veeva-domain :class:`VeevaOAuthError`.


def encrypt(plaintext: str) -> str:
    """Encrypt a string for at-rest storage. Empty -> empty (idempotent)."""
    return core_encryption.encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """Decrypt a string produced by :func:`encrypt`.

    Raises :class:`VeevaOAuthError` on tampering or key mismatch so
    callers can react to the Veeva-domain error type ; the underlying
    :class:`core.encryption.EncryptionError` is wrapped.
    """
    if not ciphertext:
        return ""
    try:
        return core_encryption.decrypt(ciphertext)
    except core_encryption.EncryptionError as exc:
        raise VeevaOAuthError(
            "Cannot decrypt Veeva OAuth credential ; check ENCRYPTION_PROVIDER "
            "/ SECRET_KEY configuration and re-run the OAuth flow."
        ) from exc


# ---------------------------------------------------------------------------
# Config helpers (env-driven, matching the rest of the Veeva integration)
# ---------------------------------------------------------------------------

def _config() -> dict:
    """Read OAuth config from env. Returns the values exactly as configured."""
    return {
        "vault_url": getattr(settings, "VEEVA_BASE_URL", "") or "",
        "client_id": os.environ.get("VEEVA_OAUTH_CLIENT_ID", "") or "",
        "client_secret": os.environ.get("VEEVA_OAUTH_CLIENT_SECRET", "") or "",
        "redirect_uri": os.environ.get("VEEVA_OAUTH_REDIRECT_URI", "") or "",
        "scope": os.environ.get("VEEVA_OAUTH_SCOPE", DEFAULT_SCOPE),
    }


def is_oauth2_enabled() -> bool:
    """Return True when VEEVA_AUTH_FLOW=oauth2 in the environment."""
    return os.environ.get("VEEVA_AUTH_FLOW", "session_id").lower() == "oauth2"


# ---------------------------------------------------------------------------
# Token singleton retrieval
# ---------------------------------------------------------------------------

def _token_record() -> "VeevaOAuthToken":
    """Return the singleton OAuth token row, creating it lazily if absent.

    The model is a singleton (one OAuth identity per Labionexus deployment
    for v1). We always operate on row pk=1.
    """
    from .models import VeevaOAuthToken
    row, _ = VeevaOAuthToken.objects.get_or_create(pk=1)
    return row


# ---------------------------------------------------------------------------
# Step 2 — Build the authorize URL
# ---------------------------------------------------------------------------

def mint_state_token() -> str:
    """Generate + persist a CSRF state token for an active auth flow."""
    state = secrets.token_urlsafe(32)
    record = _token_record()
    record.oauth_state = state
    record.oauth_state_created_at = timezone.now()
    record.save(update_fields=["oauth_state", "oauth_state_created_at", "updated_at"])
    return state


def build_authorize_url() -> str:
    """Build the URL the operator browses to begin the OAuth flow.

    Validates env config first ; raises :class:`VeevaOAuthError` when
    any of the required values are missing.
    """
    cfg = _config()
    if not cfg["vault_url"]:
        raise VeevaOAuthError(
            "VEEVA_BASE_URL is not set ; cannot build authorize URL."
        )
    if not cfg["client_id"]:
        raise VeevaOAuthError(
            "VEEVA_OAUTH_CLIENT_ID is not set ; cannot build authorize URL."
        )
    if not cfg["redirect_uri"]:
        raise VeevaOAuthError(
            "VEEVA_OAUTH_REDIRECT_URI is not set ; cannot build authorize URL."
        )

    state = mint_state_token()
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "state": state,
        "scope": cfg["scope"],
    }
    return cfg["vault_url"].rstrip("/") + OAUTH_AUTHORIZE_PATH + "?" + urlencode(params)


# ---------------------------------------------------------------------------
# Step 5 — Verify state + exchange code for tokens
# ---------------------------------------------------------------------------

def _state_is_fresh(record: "VeevaOAuthToken", inbound_state: str) -> bool:
    """Return True when the inbound state matches the persisted one + TTL."""
    if not record.oauth_state or not record.oauth_state_created_at:
        return False
    if record.oauth_state != inbound_state:
        return False
    age = timezone.now() - record.oauth_state_created_at
    return age < timedelta(minutes=STATE_TTL_MINUTES)


def exchange_code_for_tokens(code: str, state: str) -> tuple[str, str]:
    """Complete the OAuth callback : verify state, swap code for tokens.

    Persists encrypted access_token + refresh_token + expiry on the
    singleton record. Returns ``(access_token, refresh_token)`` in
    plaintext for the immediate caller. Raises :class:`VeevaOAuthError`
    on CSRF mismatch or token-endpoint failure.
    """
    cfg = _config()
    record = _token_record()

    if not _state_is_fresh(record, state):
        raise VeevaOAuthError(
            "CSRF state mismatch or expired ; restart the OAuth flow."
        )
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise VeevaOAuthError(
            "OAuth client credentials are not configured ; check "
            "VEEVA_OAUTH_CLIENT_ID and VEEVA_OAUTH_CLIENT_SECRET."
        )

    url = cfg["vault_url"].rstrip("/") + OAUTH_TOKEN_PATH
    try:
        response = requests.post(
            url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise VeevaOAuthError(f"Vault token endpoint unreachable: {exc}") from exc

    if response.status_code != 200:
        raise VeevaOAuthError(
            f"Vault token exchange HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise VeevaOAuthError("Vault token endpoint returned non-JSON") from exc

    access_token = body.get("access_token") or ""
    refresh_token = body.get("refresh_token") or ""
    expires_in = int(body.get("expires_in", 3600))
    if not access_token:
        raise VeevaOAuthError(
            f"Vault token endpoint omitted access_token: {body!r}"
        )

    record.access_token_enc = encrypt(access_token)
    if refresh_token:
        record.refresh_token_enc = encrypt(refresh_token)
    record.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
    # State is single-use ; clear it now that the swap succeeded.
    record.oauth_state = ""
    record.oauth_state_created_at = None
    record.save(update_fields=[
        "access_token_enc",
        "refresh_token_enc",
        "token_expires_at",
        "oauth_state",
        "oauth_state_created_at",
        "updated_at",
    ])
    logger.info("Veeva OAuth exchange OK (expires in %ss)", expires_in)
    return access_token, refresh_token


# ---------------------------------------------------------------------------
# Step 7 — Refresh the access token using the long-lived refresh token
# ---------------------------------------------------------------------------

def _token_is_fresh(record: "VeevaOAuthToken") -> bool:
    """True when the access token is present and not within the refresh buffer."""
    if not record.access_token_enc or not record.token_expires_at:
        return False
    buffer = timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
    return timezone.now() + buffer < record.token_expires_at


def refresh_access_token() -> str:
    """Trade the refresh_token for a fresh access_token. Persists on success."""
    cfg = _config()
    record = _token_record()

    if not record.refresh_token_enc:
        raise VeevaOAuthError(
            "No refresh token stored ; re-run the OAuth Authorization flow."
        )
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise VeevaOAuthError(
            "OAuth client credentials missing for refresh."
        )

    url = cfg["vault_url"].rstrip("/") + OAUTH_TOKEN_PATH
    try:
        response = requests.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": decrypt(record.refresh_token_enc),
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise VeevaOAuthError(f"Vault token refresh unreachable: {exc}") from exc

    if response.status_code != 200:
        raise VeevaOAuthError(
            f"Vault token refresh HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )
    body = response.json()
    access_token = body.get("access_token") or ""
    new_refresh = body.get("refresh_token") or ""
    expires_in = int(body.get("expires_in", 3600))
    if not access_token:
        raise VeevaOAuthError("Vault refresh omitted access_token")

    record.access_token_enc = encrypt(access_token)
    if new_refresh:
        record.refresh_token_enc = encrypt(new_refresh)
    record.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
    record.save(update_fields=[
        "access_token_enc",
        "refresh_token_enc",
        "token_expires_at",
        "updated_at",
    ])
    return access_token


def get_or_refresh_access_token() -> str:
    """Return a usable access token, refreshing if expired or near expiry.

    Used by the Veeva HTTP client when ``VEEVA_AUTH_FLOW=oauth2``.
    """
    record = _token_record()
    if _token_is_fresh(record):
        try:
            return decrypt(record.access_token_enc)
        except VeevaOAuthError:
            logger.warning(
                "Cached OAuth access token decrypt failed ; refreshing"
            )
    return refresh_access_token()


def invalidate_cached_token() -> None:
    """Clear the cached access token expiry so the next call forces a refresh.

    Used by the HTTP client when it gets a 401 from Vault — that signals
    the cached token went stale before its expected TTL.
    """
    record = _token_record()
    record.token_expires_at = None
    record.save(update_fields=["token_expires_at", "updated_at"])
