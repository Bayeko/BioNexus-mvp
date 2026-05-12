from __future__ import annotations

from django.conf import settings

from modules.integrations.base.service import push_to_vendor
from modules.integrations.veeva.models import IntegrationPushLog

from .client import build_empower_client
from .field_mapping import measurement_to_result


def push_measurement(measurement) -> IntegrationPushLog:
    client = build_empower_client()
    payload = measurement_to_result(measurement)
    return push_to_vendor(
        vendor=IntegrationPushLog.VENDOR_EMPOWER,
        target_object_type=IntegrationPushLog.TARGET_GENERIC_RESULT,
        source_measurement_id=getattr(measurement, "id", None),
        source_report_id=None,
        payload=payload,
        client=client,
        mode_label=str(getattr(settings, "EMPOWER_MODE", "disabled")).lower(),
        push_callable=lambda c: c.push_object(payload),
    )
