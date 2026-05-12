"""Vendor-agnostic push orchestration.

This wraps the (mapping → idempotency-check → client.push → log update)
loop that every connector follows. Vendors expose thin wrappers that
call ``push_to_vendor`` with their vendor name + mapper + client factory.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from django.utils import timezone

from modules.integrations.veeva.models import IntegrationPushLog

from .client import BaseLimsClient
from .signing import payload_hash

log = logging.getLogger("integrations.service")


def push_to_vendor(
    *,
    vendor: str,
    target_object_type: str,
    source_measurement_id: Optional[int],
    source_report_id: Optional[int],
    payload: dict,
    client: BaseLimsClient,
    mode_label: str,
    push_callable: Callable[[BaseLimsClient], Any],
) -> IntegrationPushLog:
    """Run one push attempt with idempotency + log persistence.

    Returns the IntegrationPushLog row (created or updated).
    """
    p_hash = payload_hash(payload)

    existing = (
        IntegrationPushLog.objects
        .filter(vendor=vendor, payload_hash=p_hash)
        .order_by("-created_at")
        .first()
    )
    if existing and existing.status == IntegrationPushLog.STATUS_SUCCESS:
        log.info(
            "%s push deduped — already in %s as %s",
            vendor,
            vendor,
            existing.target_object_id,
        )
        return existing

    record = existing or IntegrationPushLog.objects.create(
        vendor=vendor,
        target_object_type=target_object_type,
        source_measurement_id=source_measurement_id,
        source_report_id=source_report_id,
        payload_hash=p_hash,
        status=IntegrationPushLog.STATUS_PENDING,
        mode=mode_label,
    )

    record.status = IntegrationPushLog.STATUS_IN_FLIGHT
    record.attempts = (record.attempts or 0) + 1
    record.last_attempt_at = timezone.now()
    record.mode = mode_label
    record.save(
        update_fields=["status", "attempts", "last_attempt_at", "mode"]
    )

    result = push_callable(client)

    record.http_status = result.http_status
    record.response_body_excerpt = result.response_body_excerpt or ""
    record.last_error = result.error or ""
    if result.ok:
        record.status = IntegrationPushLog.STATUS_SUCCESS
        record.target_object_id = result.vault_id or ""
        record.succeeded_at = timezone.now()
    else:
        record.status = IntegrationPushLog.STATUS_FAILED
    record.save()
    return record
