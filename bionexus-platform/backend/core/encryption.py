"""Pluggable at-rest encryption for sensitive credentials.

Default backend derives a key from Django's ``SECRET_KEY`` (matches the
pre-existing Veeva OAuth behaviour ; zero migration needed). Other
backends are available for production deployments that require stronger
key management:

============== ====================================================
Provider         Use case
============== ====================================================
``secret_key``  Default. Fernet key derived from ``SECRET_KEY``.
                Good enough for demo + early customers ; rotating
                ``SECRET_KEY`` requires re-running OAuth flows.
``env_key``     Fernet key read directly from ``ENCRYPTION_KEY``
                env var (must be a valid 32-byte urlsafe-b64 string).
                Lets you rotate the encryption key without touching
                ``SECRET_KEY``.
``gcp_kms``     Stub. Wraps ``google-cloud-kms`` symmetric encrypt /
                decrypt calls. Activated when ``ENCRYPTION_PROVIDER
                =gcp_kms`` and all four ``GCP_KMS_*`` env vars are
                set + ``google-cloud-kms`` is installed. Documented
                migration path for procurement reviews that ask
                "where is the HSM ?".
============== ====================================================

Configuration ::

    ENCRYPTION_PROVIDER     = secret_key  (default) | env_key | gcp_kms
    ENCRYPTION_KEY          = <urlsafe-b64 32-byte key>  (env_key only)
    GCP_KMS_PROJECT_ID      = ...                        (gcp_kms only)
    GCP_KMS_LOCATION        = ...                        (gcp_kms only)
    GCP_KMS_KEY_RING        = ...                        (gcp_kms only)
    GCP_KMS_KEY_NAME        = ...                        (gcp_kms only)

All providers expose the same two operations: ``encrypt(plaintext) ->
ciphertext`` and ``decrypt(ciphertext) -> plaintext``. The format of
``ciphertext`` is opaque to the caller and prefixed with the provider
name + version so we can migrate between backends if needed (a future
rotation script can read the prefix to dispatch the right decrypt).

For pre-PMF deployments the default ``secret_key`` provider is
intentionally simple. For customer-deal procurement reviews that ask
about HSM, point them at this module: the abstraction is in place, the
GCP KMS path is one env-var flip + 1 pip install away.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger("core.encryption")


# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------

class EncryptionError(RuntimeError):
    """Raised when encrypt / decrypt cannot complete.

    Decrypt failures typically mean either tampering or a key change
    (rotated ``SECRET_KEY``, swapped provider, missing env var). The
    error message is safe to surface in operator-facing UIs : it never
    contains the plaintext or the key.
    """


# ---------------------------------------------------------------------------
# KeyProvider interface
# ---------------------------------------------------------------------------

class KeyProvider(ABC):
    """Two-method symmetric encryption interface.

    Each concrete provider tags its output with a short prefix so a
    future migration script can route a stored ciphertext to the right
    decrypt path. The prefix is part of the ciphertext, not metadata —
    swallowing it during decrypt is the provider's responsibility.
    """

    #: Short identifier prepended to ciphertext, e.g. "sk1$<rest>".
    prefix: str = ""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string. Empty input returns empty output."""

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string. Empty input returns empty output."""

    def _strip_prefix(self, ciphertext: str) -> str:
        if self.prefix and ciphertext.startswith(self.prefix + "$"):
            return ciphertext[len(self.prefix) + 1:]
        return ciphertext

    def _add_prefix(self, blob: str) -> str:
        return f"{self.prefix}${blob}" if self.prefix else blob


# ---------------------------------------------------------------------------
# Provider 1 — SECRET_KEY derived Fernet (default)
# ---------------------------------------------------------------------------

class SecretKeyDerivedKeyProvider(KeyProvider):
    """Fernet key derived from Django ``SECRET_KEY`` via SHA-256.

    Pros : zero configuration, works out of the box.
    Cons : rotating ``SECRET_KEY`` invalidates all stored ciphertext,
    no separation of concerns between session signing key and
    encryption key.
    """

    prefix = "sk1"

    def _fernet(self) -> Fernet:
        raw = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(raw))

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        blob = self._fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return self._add_prefix(blob)

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        body = self._strip_prefix(ciphertext)
        try:
            return self._fernet().decrypt(body.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise EncryptionError(
                "Cannot decrypt ciphertext with the current SECRET_KEY. "
                "If SECRET_KEY rotated, re-run any flow that produced "
                "encrypted artefacts (e.g. OAuth authorization)."
            ) from exc


# ---------------------------------------------------------------------------
# Provider 2 — Dedicated ENCRYPTION_KEY env var
# ---------------------------------------------------------------------------

class EnvKeyProvider(KeyProvider):
    """Fernet key read directly from ``ENCRYPTION_KEY`` env var.

    The env var must contain a urlsafe-base64-encoded 32-byte key (the
    Fernet default). Generate one via ``Fernet.generate_key()``.

    Pros : decoupled from ``SECRET_KEY``, rotation is a single env var
    swap (with a re-encryption migration).
    Cons : the key is still in process memory + env vars.
    """

    prefix = "ek1"

    def _fernet(self) -> Fernet:
        key = os.environ.get("ENCRYPTION_KEY", "")
        if not key:
            raise EncryptionError(
                "ENCRYPTION_PROVIDER=env_key but ENCRYPTION_KEY env var is empty."
            )
        try:
            return Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise EncryptionError(
                "ENCRYPTION_KEY is not a valid 32-byte urlsafe-base64 Fernet key. "
                "Generate one via cryptography.fernet.Fernet.generate_key()."
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        blob = self._fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return self._add_prefix(blob)

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        body = self._strip_prefix(ciphertext)
        try:
            return self._fernet().decrypt(body.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise EncryptionError(
                "Cannot decrypt ciphertext with the current ENCRYPTION_KEY. "
                "Either the value rotated or the ciphertext was tampered."
            ) from exc


# ---------------------------------------------------------------------------
# Provider 3 — Google Cloud KMS (stub, opt-in)
# ---------------------------------------------------------------------------

class GcpKmsKeyProvider(KeyProvider):
    """Google Cloud KMS-backed encryption.

    Stubbed v1 : raises :class:`EncryptionError` if the
    ``google-cloud-kms`` package isn't installed or if any of the four
    GCP env vars is missing. When everything is wired up correctly the
    implementation calls ``client.encrypt(name, plaintext)`` /
    ``client.decrypt(name, ciphertext)`` — full doc + activation
    procedure in this module's docstring.

    Activation steps (post-procurement) ::

        1. pip install google-cloud-kms>=2.0
        2. Provision the key in GCP : project / location / key_ring / key_name
        3. Grant the service account roles/cloudkms.cryptoKeyEncrypterDecrypter
        4. Set 4 env vars + ENCRYPTION_PROVIDER=gcp_kms
        5. Run the migration script: manage.py rotate_encryption --from sk1 --to gk1

    Why a stub : real GCP KMS calls cost money and require a configured
    GCP project. Shipping the abstraction now lets us answer
    procurement reviews ("yes, we support HSM-backed key management,
    here's the code path") without provisioning anything pre-deal.
    """

    prefix = "gk1"

    def _client_and_name(self):
        try:
            from google.cloud import kms_v1 as kms
        except ImportError as exc:
            raise EncryptionError(
                "GCP KMS provider requires google-cloud-kms : "
                "pip install google-cloud-kms>=2.0"
            ) from exc

        project = os.environ.get("GCP_KMS_PROJECT_ID")
        location = os.environ.get("GCP_KMS_LOCATION")
        key_ring = os.environ.get("GCP_KMS_KEY_RING")
        key_name = os.environ.get("GCP_KMS_KEY_NAME")
        missing = [
            name for name, val in [
                ("GCP_KMS_PROJECT_ID", project),
                ("GCP_KMS_LOCATION", location),
                ("GCP_KMS_KEY_RING", key_ring),
                ("GCP_KMS_KEY_NAME", key_name),
            ]
            if not val
        ]
        if missing:
            raise EncryptionError(
                "GCP KMS provider missing env vars: " + ", ".join(missing)
            )

        client = kms.KeyManagementServiceClient()
        name = client.crypto_key_path(project, location, key_ring, key_name)
        return client, name

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        client, name = self._client_and_name()
        resp = client.encrypt(request={"name": name, "plaintext": plaintext.encode("utf-8")})
        body = base64.b64encode(resp.ciphertext).decode("utf-8")
        return self._add_prefix(body)

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        client, name = self._client_and_name()
        body = self._strip_prefix(ciphertext)
        try:
            blob = base64.b64decode(body.encode("utf-8"))
        except ValueError as exc:
            raise EncryptionError("GCP KMS ciphertext is not valid base64") from exc
        try:
            resp = client.decrypt(request={"name": name, "ciphertext": blob})
        except Exception as exc:  # pragma: no cover - depends on real GCP
            raise EncryptionError(f"GCP KMS decrypt failed: {exc}") from exc
        return resp.plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[KeyProvider]] = {
    "secret_key": SecretKeyDerivedKeyProvider,
    "env_key": EnvKeyProvider,
    "gcp_kms": GcpKmsKeyProvider,
}


def _resolve_provider_name() -> str:
    """Resolve which provider to use, with explicit precedence.

    1. ``settings.ENCRYPTION_PROVIDER`` if set (override-friendly for tests)
    2. ``ENCRYPTION_PROVIDER`` env var
    3. fallback "secret_key"
    """
    name = (
        getattr(settings, "ENCRYPTION_PROVIDER", None)
        or os.environ.get("ENCRYPTION_PROVIDER")
        or "secret_key"
    )
    return name.lower()


def get_key_provider() -> KeyProvider:
    """Return the configured KeyProvider.

    Not cached : settings overrides during tests need to be live. The
    provider instances themselves are cheap to construct (the heavyweight
    work — fetching a Fernet key, opening a GCP client — happens lazily
    on the first encrypt or decrypt call).
    """
    name = _resolve_provider_name()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise EncryptionError(
            f"Unknown ENCRYPTION_PROVIDER={name!r}. "
            f"Valid options: {sorted(_PROVIDERS)}"
        )
    return cls()


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def encrypt(plaintext: str) -> str:
    """Encrypt with the currently configured provider."""
    return get_key_provider().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """Decrypt with the currently configured provider.

    Routes by ciphertext prefix when present so a freshly-rotated
    deployment can still read the old format until a migration script
    re-encrypts everything.
    """
    if not ciphertext:
        return ""
    # Route by stored prefix when present : a deployment mid-migration
    # may still hold old-format rows.
    for prefix, cls in [(c.prefix, c) for c in _PROVIDERS.values()]:
        if prefix and ciphertext.startswith(prefix + "$"):
            return cls().decrypt(ciphertext)
    # No prefix : fall back to the configured provider (legacy data
    # from before the prefix was introduced).
    return get_key_provider().decrypt(ciphertext)
