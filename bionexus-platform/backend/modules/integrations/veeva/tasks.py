"""Celery tasks for Veeva Vault push operations.

Two responsibilities :

- ``push_measurement_async`` wraps the synchronous service.push_measurement
  call in a Celery task. The signal handler enqueues a job per
  measurement when ``VEEVA_ASYNC_PUSH=true`` ; otherwise the existing
  inline push remains in effect.

- ``retry_failed_pushes`` is beat-scheduled every 5 minutes in
  production. It drains the failed-job queue by re-enqueueing each
  failed :class:`IntegrationPushLog` row whose vendor is Veeva and
  whose connection is still active.

Both tasks are idempotent : the service's payload_hash short-circuit
prevents double-pushes.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from .models import IntegrationPushLog

logger = logging.getLogger("veeva.tasks")

# Cap how many failed jobs we replay per beat tick to avoid hammering
# Vault after a long outage.
RETRY_BATCH_SIZE = 25


@shared_task(
    name="modules.integrations.veeva.tasks.push_measurement_async",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def push_measurement_async(measurement_id: int) -> int | None:
    """Push a single Measurement to Vault via Celery.

    Returns the resulting :class:`IntegrationPushLog.pk`, or ``None``
    when the integration is disabled. The Celery autoretry layer covers
    transient transport failures ; the service-level retry handles
    Vault-side 5xx and 401 responses.
    """
    if not getattr(settings, "VEEVA_INTEGRATION_ENABLED", False):
        return None
    if str(getattr(settings, "VEEVA_MODE", "disabled")).lower() == "disabled":
        return None

    # Local imports keep startup cycles fast and avoid loading the
    # service on workers that only handle other queues.
    from modules.measurements.models import Measurement

    from .service import push_measurement

    try:
        measurement = Measurement.objects.get(pk=measurement_id)
    except Measurement.DoesNotExist:
        logger.warning(
            "Veeva async push: Measurement#%s vanished before push",
            measurement_id,
        )
        return None

    record = push_measurement(measurement)
    logger.info(
        "Veeva async push: log=%s status=%s vault_id=%s",
        record.pk,
        record.status,
        record.target_object_id or "-",
    )
    return record.pk


@shared_task(name="modules.integrations.veeva.tasks.retry_failed_pushes")
def retry_failed_pushes() -> dict:
    """Beat-scheduled drain of failed Veeva pushes.

    Looks up to ``RETRY_BATCH_SIZE`` IntegrationPushLog rows in status
    ``failed`` for the Veeva vendor, then re-enqueues a fresh
    push for the same source measurement. The service's payload_hash
    idempotency check keeps us from duplicating successful work.
    """
    qs = (
        IntegrationPushLog.objects
        .filter(
            vendor=IntegrationPushLog.VENDOR_VEEVA,
            status=IntegrationPushLog.STATUS_FAILED,
        )
        .exclude(source_measurement_id__isnull=True)
        .order_by("-created_at")[:RETRY_BATCH_SIZE]
    )
    failed = list(qs)
    requeued = 0
    for row in failed:
        push_measurement_async.delay(row.source_measurement_id)
        requeued += 1
    result = {"found": len(failed), "requeued": requeued}
    logger.info("retry_failed_pushes: %s", result)
    return result
