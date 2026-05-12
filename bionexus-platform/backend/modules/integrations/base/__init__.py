"""Shared building blocks for every LIMS / QMS / ELN connector.

Each vendor module under ``modules/integrations/<vendor>/`` reuses these
primitives so adding a new connector is mostly: write a field mapper +
a thin client subclass + a mock route extension.

Re-exports the public API of the package for ergonomic imports:

    from modules.integrations.base import BaseLimsClient, PushResult, build_client
"""

from .client import (
    BaseLimsClient,
    DisabledLimsClient,
    HttpLimsClient,
    PushResult,
    build_client,
)
from .service import push_to_vendor
from .signing import canonicalize, compute_signature, payload_hash, verify_signature

__all__ = [
    "BaseLimsClient",
    "DisabledLimsClient",
    "HttpLimsClient",
    "PushResult",
    "build_client",
    "push_to_vendor",
    "canonicalize",
    "compute_signature",
    "payload_hash",
    "verify_signature",
]
