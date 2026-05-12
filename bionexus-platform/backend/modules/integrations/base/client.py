"""Vendor-agnostic HTTP client base for every LIMS / QMS / ELN connector.

A new vendor typically only needs to subclass :class:`HttpLimsClient`,
set ``vendor`` + ``object_path``, override ``_auth_headers`` if needed,
and ship a field mapper. The push primitives, retry hooks, transport
error handling, and signature header are all inherited.

The factory :func:`build_client` reads ``<VENDOR>_MODE`` (and friends)
from Django settings so callers never branch on mode themselves.
"""

from __future__ import annotations

import json as _json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from .signing import compute_signature

log = logging.getLogger("integrations.base")


@dataclass
class PushResult:
    """Uniform return shape across every client mode + every vendor."""

    ok: bool
    http_status: Optional[int]
    vault_id: str = ""          # generic external object ID returned by the vendor
    error: str = ""
    response_body_excerpt: str = ""
    latency_ms: int = 0

    def __bool__(self) -> bool:
        return self.ok


# ---------------------------------------------------------------------------

class BaseLimsClient(ABC):
    """Push-only abstract client. Every concrete client implements at least
    ``push_object`` — additional kinds (document attachments, etc.) are
    optional and may raise NotImplementedError on vendors that don't
    support them.
    """

    vendor: str = "abstract"
    mode: str = "abstract"

    @abstractmethod
    def push_object(self, payload: dict) -> PushResult:
        """Push the primary measurement-like object to the vendor."""

    def push_document(self, payload: dict, file_bytes: bytes) -> PushResult:
        """Optional — most LIMS vendors accept attachments, ELN vendors don't."""
        return PushResult(
            ok=False,
            http_status=None,
            error=f"{self.vendor} client does not implement push_document",
        )


# ---------------------------------------------------------------------------

class DisabledLimsClient(BaseLimsClient):
    """Production-safe no-op. Used when ``<VENDOR>_MODE=disabled``."""

    mode = "disabled"

    def __init__(self, vendor: str = "disabled") -> None:
        self.vendor = vendor

    def push_object(self, payload: dict) -> PushResult:  # noqa: ARG002
        return PushResult(
            ok=False,
            http_status=None,
            error=f"{self.vendor}_MODE=disabled - push skipped",
        )

    def push_document(self, payload: dict, file_bytes: bytes) -> PushResult:  # noqa: ARG002
        return PushResult(
            ok=False,
            http_status=None,
            error=f"{self.vendor}_MODE=disabled - push skipped",
        )


# ---------------------------------------------------------------------------

class HttpLimsClient(BaseLimsClient):
    """HTTP client base.

    Subclasses set ``vendor``, ``object_path`` (the URL suffix for the
    primary push), and ``document_path`` (optional). Auth scheme is
    controlled by overriding :meth:`_auth_headers`.
    """

    object_path: str = ""
    document_path: str = ""

    def __init__(
        self,
        base_url: str,
        shared_secret: str = "",
        timeout_s: float = 10.0,
        mode: str = "mock",
    ) -> None:
        if requests is None:
            raise RuntimeError(
                "'requests' is required for HTTP LIMS clients. "
                "It is pinned in backend/requirements.txt."
            )
        self.base_url = base_url.rstrip("/")
        self.shared_secret = shared_secret
        self.timeout_s = timeout_s
        self.mode = mode

    # ---- auth -----------------------------------------------------------

    def _auth_headers(self) -> dict:
        """Default headers — every subclass calls super()._auth_headers()."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-BioNexus-Source": "lbn-gateway",
            "X-BioNexus-Vendor": self.vendor,
        }

    # ---- push ----------------------------------------------------------

    def push_object(self, payload: dict) -> PushResult:
        if not self.object_path:
            raise NotImplementedError(
                f"{self.__class__.__name__} did not set object_path"
            )
        return self._post_json(self.object_path, payload)

    def push_document(self, payload: dict, file_bytes: bytes) -> PushResult:
        if not self.document_path:
            return super().push_document(payload, file_bytes)
        url = self.base_url + self.document_path
        headers = self._auth_headers()
        headers.pop("Content-Type", None)  # let requests set multipart boundary
        if self.shared_secret:
            headers["X-BioNexus-Signature"] = compute_signature(
                payload, self.shared_secret
            )
        files = {
            "metadata": ("metadata.json", _json_bytes(payload), "application/json"),
            "file": ("attachment.bin", file_bytes, "application/pdf"),
        }
        return self._send("POST", url, headers=headers, files=files)

    # ---- internals -----------------------------------------------------

    def _post_json(self, path: str, payload: dict) -> PushResult:
        url = self.base_url + path
        headers = self._auth_headers()
        if self.shared_secret:
            headers["X-BioNexus-Signature"] = compute_signature(
                payload, self.shared_secret
            )
        return self._send("POST", url, headers=headers, json=payload)

    def _send(self, method: str, url: str, **kwargs) -> PushResult:
        kwargs.setdefault("timeout", self.timeout_s)
        started = time.perf_counter()
        try:
            response = requests.request(method, url, **kwargs)  # type: ignore[union-attr]
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log.warning("%s push transport error: %s", self.vendor, exc)
            return PushResult(
                ok=False,
                http_status=None,
                error=f"transport: {exc.__class__.__name__}: {exc}",
                latency_ms=elapsed_ms,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        excerpt = response.text[:2048] if response.text else ""
        vault_id = self._extract_id(response) if response.ok else ""
        return PushResult(
            ok=response.ok,
            http_status=response.status_code,
            vault_id=vault_id,
            response_body_excerpt=excerpt,
            error="" if response.ok else f"HTTP {response.status_code}",
            latency_ms=elapsed_ms,
        )

    def _extract_id(self, response: Any) -> str:
        """Default: look for ``id`` at the JSON root. Vendors with different
        envelopes override this — e.g. Empower nests under ``result.id``.
        """
        try:
            data = response.json()
        except (ValueError, AttributeError):
            return ""
        if isinstance(data, dict):
            return str(data.get("id", ""))
        return ""


# ---------------------------------------------------------------------------

def build_client(
    vendor: str,
    *,
    client_class: type[HttpLimsClient],
    settings_prefix: Optional[str] = None,
) -> BaseLimsClient:
    """Pick the right client for ``vendor`` based on Django settings.

    ``settings_prefix`` defaults to ``vendor.upper()`` — e.g. for vendor
    ``"empower"`` we read ``EMPOWER_MODE``, ``EMPOWER_BASE_URL``,
    ``EMPOWER_SHARED_SECRET``. Override only for vendors with a
    non-standard naming convention.
    """
    from django.conf import settings

    prefix = (settings_prefix or vendor).upper()
    mode = str(getattr(settings, f"{prefix}_MODE", "disabled")).lower()
    base_url = getattr(settings, f"{prefix}_BASE_URL", "")
    secret = getattr(settings, f"{prefix}_SHARED_SECRET", "")

    if mode == "disabled":
        return DisabledLimsClient(vendor=vendor)
    if not base_url:
        log.warning("%s_MODE=%s but %s_BASE_URL empty — disabling", prefix, mode, prefix)
        return DisabledLimsClient(vendor=vendor)
    if mode == "prod" and os.environ.get(f"{prefix}_PROD_CONFIRMED", "").lower() != "true":
        log.error(
            "%s_MODE=prod requires %s_PROD_CONFIRMED=true. Refusing to push to prod by accident.",
            prefix,
            prefix,
        )
        return DisabledLimsClient(vendor=vendor)
    if mode not in {"mock", "sandbox", "prod"}:
        log.warning("Unknown %s_MODE=%r — disabling", prefix, mode)
        return DisabledLimsClient(vendor=vendor)

    return client_class(base_url=base_url, shared_secret=secret, mode=mode)


# ---------------------------------------------------------------------------

def _json_bytes(payload: dict) -> bytes:
    return _json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
