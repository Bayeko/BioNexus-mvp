"""Veeva signing — now a re-export of the shared base primitives.

Kept as a thin wrapper so existing imports
``from modules.integrations.veeva.signing import ...`` keep working
without forcing every existing test to be touched.
"""

from modules.integrations.base.signing import (  # noqa: F401
    canonicalize,
    compute_signature,
    payload_hash,
    verify_signature,
)
