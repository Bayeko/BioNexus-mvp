from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

log = logging.getLogger("empower.signals")


@receiver(post_save, sender="measurements.Measurement", dispatch_uid="empower_push_measurement")
def push_measurement_to_empower(sender, instance, created, **kwargs):
    if not created:
        return
    if not getattr(settings, "EMPOWER_INTEGRATION_ENABLED", False):
        return
    if str(getattr(settings, "EMPOWER_MODE", "disabled")).lower() == "disabled":
        return

    from .service import push_measurement

    try:
        push_measurement(instance)
    except Exception:  # noqa: BLE001
        log.exception(
            "Empower push failed for Measurement#%s - logged, write path continues",
            getattr(instance, "id", "?"),
        )
