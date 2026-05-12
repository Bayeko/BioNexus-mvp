from __future__ import annotations

from django.conf import settings

from modules.integrations.base.service import push_to_vendor
from modules.integrations.veeva.models import IntegrationPushLog

from .client import build_benchling_client
from .field_mapping import measurement_to_result_row


def push_measurement(measurement) -> IntegrationPushLog:
    client = build_benchling_client()
    payload = measurement_to_result_row(measurement)
    return push_to_vendor(
        vendor=IntegrationPushLog.VENDOR_BENCHLING,
        target_object_type=IntegrationPushLog.TARGET_GENERIC_ENTRY,
        source_measurement_id=getattr(measurement, "id", None),
        source_report_id=None,
        payload=payload,
        client=client,
        mode_label=str(getattr(settings, "BENCHLING_MODE", "disabled")).lower(),
        push_callable=lambda c: c.push_object(payload),
    )
