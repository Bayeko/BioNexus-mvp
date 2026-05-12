"""Canonical-JSON HMAC-SHA256 — shared by every vendor that uses it.

This is the same implementation that originally lived in
``modules/integrations/veeva/signing.py``. Hoisted here so LabWare,
STARLIMS, etc. can use the same primitives without copy-paste.

The Veeva-specific module now re-exports these names so existing
imports keep working.
"""

from __future__ import annotations

import hashlib
import hmac
import json


def canonicalize(payload: dict) -> bytes:
    """Return the canonical UTF-8 bytes form of ``payload``."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def payload_hash(payload: dict) -> str:
    """SHA-256 hex digest of the canonical payload — used as idempotency key."""
    return hashlib.sha256(canonicalize(payload)).hexdigest()


def compute_signature(payload: dict, secret: str) -> str:
    """HMAC-SHA256(payload, secret) as ``sha256=<hex>``.

    Raises ValueError on empty secret — every vendor we support either
    uses HMAC or a bearer token; either way an empty secret in HMAC mode
    is misconfiguration, not a valid state.
    """
    if not secret:
        raise ValueError(
            "Empty signing secret. Set the vendor's *_SHARED_SECRET env var."
        )
    mac = hmac.new(
        secret.encode("utf-8"),
        canonicalize(payload),
        hashlib.sha256,
    )
    return f"sha256={mac.hexdigest()}"


def verify_signature(payload: dict, secret: str, signature: str) -> bool:
    """Constant-time verification of an incoming signature."""
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, signature)
