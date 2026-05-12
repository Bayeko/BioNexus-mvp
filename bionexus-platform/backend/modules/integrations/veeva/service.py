"""High-level push orchestration for Veeva Vault.

This module is the **only** place outside ``client.py`` that knows how
to push something to Vault. Signal handlers, views, management commands,
and demo scripts all go through here.

Responsibilities:
  - Translate a domain object (Measurement, CertifiedReport) to a Vault
    payload via :mod:`field_mapping`
  - Compute the idempotency hash so a retry doesn't double-push
  - Create / update an :class:`IntegrationPushLog` row
  - Dispatch to the right :class:`VeevaClient` for the active mode
  - Record the result on the log row

Notes on idempotency: we look up an existing log row by
``payload_hash``. If one exists with status ``success``, we return it
unchanged — Vault already has the object, retrying would be a duplicate.
If one exists with status ``failed`` or ``dead_letter``, we increment
``attempts`` on the same row. If none exists, we create a new one.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .client import VeevaClient, build_client_from_settings
from .field_mapping import (
    measurement_to_quality_event,
    report_to_document,
)
from .models import IntegrationPushLog
from .signing import payload_hash

log = logging.getLogger("veeva.service")


def push_measurement(
    measurement,
    *,
    client: Optional[VeevaClient] = None,
) -> IntegrationPushLog:
    """Push a Measurement as a ``quality_event__v`` to Vault.

    Returns the :class:`IntegrationPushLog` row that records the attempt.
    Safe to call repeatedly for the same Measurement — the idempotency
    hash short-circuits duplicate pushes.

    ``client`` is injectable for tests; in production the factory builds
    the right one based on ``VEEVA_MODE``.
    """
    payload = measurement_to_quality_event(measurement)
    p_hash = payload_hash(payload)

    # Idempotency check.
    existing = (
        IntegrationPushLog.objects
        .filter(payload_hash=p_hash)
        .order_by("-created_at")
        .first()
    )
    if existing and existing.status == IntegrationPushLog.STATUS_SUCCESS:
        log.info(
            "Veeva push deduped — measurement %s already in Vault as %s",
            getattr(measurement, "id", "?"),
            existing.target_object_id,
        )
        return existing

    record = existing or IntegrationPushLog.objects.create(
        target_object_type=IntegrationPushLog.TARGET_QUALITY_EVENT,
        source_measurement_id=getattr(measurement, "id", None),
        payload_hash=p_hash,
        status=IntegrationPushLog.STATUS_PENDING,
        mode=_current_mode(),
    )

    return _execute_push(
        record=record,
        client=client or build_client_from_settings(),
        push_callable=lambda c: c.push_quality_event(payload),
    )


def push_report(
    report,
    pdf_bytes: bytes,
    *,
    client: Optional[VeevaClient] = None,
) -> IntegrationPushLog:
    """Push a CertifiedReport PDF as a ``document__v`` to Vault."""
    payload = report_to_document(report)
    p_hash = payload_hash(payload)

    existing = (
        IntegrationPushLog.objects
        .filter(payload_hash=p_hash)
        .order_by("-created_at")
        .first()
    )
    if existing and existing.status == IntegrationPushLog.STATUS_SUCCESS:
        return existing

    record = existing or IntegrationPushLog.objects.create(
        target_object_type=IntegrationPushLog.TARGET_DOCUMENT,
        source_report_id=getattr(report, "id", None),
        payload_hash=p_hash,
        status=IntegrationPushLog.STATUS_PENDING,
        mode=_current_mode(),
    )

    return _execute_push(
        record=record,
        client=client or build_client_from_settings(),
        push_callable=lambda c: c.push_document(payload, pdf_bytes),
    )


def _execute_push(
    *,
    record: IntegrationPushLog,
    client: VeevaClient,
    push_callable,
) -> IntegrationPushLog:
    """Run one push attempt, persist the outcome on the log record."""
    record.status = IntegrationPushLog.STATUS_IN_FLIGHT
    record.attempts = (record.attempts or 0) + 1
    record.last_attempt_at = timezone.now()
    record.mode = _current_mode()
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
    elif client.mode == "disabled":
        # No-op client: not a real failure. Keep the row "failed" so the
        # UI can show it was skipped due to mode, without retries.
        record.status = IntegrationPushLog.STATUS_FAILED
    else:
        # Real failure. The decision to retry happens upstream (signals
        # / scheduled task) — service.py just records state.
        record.status = IntegrationPushLog.STATUS_FAILED

    record.save()
    log.info(
        "Veeva push %s id=%s vault_id=%s http=%s",
        "OK" if result.ok else "FAIL",
        record.id,
        record.target_object_id or "-",
        record.http_status,
    )
    return record


def _current_mode() -> str:
    return str(getattr(settings, "VEEVA_MODE", "disabled")).lower()
