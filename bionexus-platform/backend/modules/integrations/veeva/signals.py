"""Signal handlers — wired in apps.py:ready().

Wires ``post_save(Measurement)`` to either the synchronous service
:func:`service.push_measurement` (default) or the async Celery task
:func:`tasks.push_measurement_async` (when ``VEEVA_ASYNC_PUSH=true``).

The handler is a thin shim :

  - Short-circuits when the integration is disabled (no DB write, no
    log noise)
  - Only fires on **create**, not on update — Vault treats events as
    immutable, and updates to a measurement after the fact would create
    duplicate quality events
  - Swallows exceptions so a Vault outage cannot poison the BioNexus
    write path. The push attempt is still recorded in IntegrationPushLog
    so an operator can retry later.

Sync vs async mode :
  - **sync** (default, ``VEEVA_ASYNC_PUSH=false``) : the push runs
    inline in the request that wrote the measurement. Lower latency
    for small fleets, no broker needed.
  - **async** (``VEEVA_ASYNC_PUSH=true``) : the push is enqueued via
    Celery. Requires a running ``celery worker``. In dev + CI the
    worker is eager so the call still happens synchronously, just
    through the task layer.
"""

from __future__ import annotations

import logging
import os

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

log = logging.getLogger("veeva.signals")


def _async_push_enabled() -> bool:
    return os.environ.get("VEEVA_ASYNC_PUSH", "false").lower() == "true"


@receiver(post_save, sender="measurements.Measurement")
def push_measurement_to_vault(sender, instance, created, **kwargs):
    """Fire-and-forget Vault push on Measurement creation."""
    if not created:
        return
    if not getattr(settings, "VEEVA_INTEGRATION_ENABLED", False):
        return
    if str(getattr(settings, "VEEVA_MODE", "disabled")).lower() == "disabled":
        return

    measurement_id = getattr(instance, "id", None)

    if _async_push_enabled():
        # Local import : Celery is optional at runtime.
        try:
            from .tasks import push_measurement_async

            push_measurement_async.delay(measurement_id)
        except Exception:  # noqa: BLE001
            log.exception(
                "Veeva async enqueue failed for Measurement#%s — "
                "falling back to inline push.",
                measurement_id,
            )
        else:
            return

    # Inline path. Local import to avoid loading the service (and its
    # Django ORM touches) at module-import time, which would race app
    # loading.
    from .service import push_measurement

    try:
        push_measurement(instance)
    except Exception:  # noqa: BLE001 — never let a Vault failure break the write path
        log.exception(
            "Veeva push failed for Measurement#%s — logged, BioNexus write continues",
            measurement_id,
        )
