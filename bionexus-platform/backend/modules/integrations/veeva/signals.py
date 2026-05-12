"""Signal handlers — wired in apps.py:ready().

Wires ``post_save(Measurement)`` to :func:`service.push_measurement` so
that every new measurement automatically attempts a Vault push when
``VEEVA_INTEGRATION_ENABLED`` is true. The handler is a thin shim:

  - Short-circuits when the integration is disabled (no DB write, no
    log noise)
  - Only fires on **create**, not on update — Vault treats events as
    immutable, and updates to a measurement after the fact would create
    duplicate quality events
  - Swallows exceptions so a Vault outage cannot poison the BioNexus
    write path. The push attempt is still recorded in IntegrationPushLog
    so an operator can retry later.

In an environment with a task queue (Celery / RQ / etc.) the push call
would be enqueued instead of run inline. For v1 we run inline because
the spec is push-only and the backend write path already does many
small synchronous writes (audit chain, etc.).
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

log = logging.getLogger("veeva.signals")


@receiver(post_save, sender="measurements.Measurement")
def push_measurement_to_vault(sender, instance, created, **kwargs):
    """Fire-and-forget Vault push on Measurement creation."""
    if not created:
        return
    if not getattr(settings, "VEEVA_INTEGRATION_ENABLED", False):
        return
    if str(getattr(settings, "VEEVA_MODE", "disabled")).lower() == "disabled":
        return

    # Local import to avoid loading the service (and its Django ORM
    # touches) at module-import time, which would race app loading.
    from .service import push_measurement

    try:
        push_measurement(instance)
    except Exception:  # noqa: BLE001 — never let a Vault failure break the write path
        log.exception(
            "Veeva push failed for Measurement#%s — logged, BioNexus write continues",
            getattr(instance, "id", "?"),
        )
