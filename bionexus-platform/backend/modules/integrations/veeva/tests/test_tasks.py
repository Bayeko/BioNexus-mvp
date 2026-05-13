"""Tests for the Celery tasks that wrap Veeva push operations.

All tests run with ``CELERY_TASK_ALWAYS_EAGER=True`` (the project
default in dev + tests) so ``task.delay(...)`` executes inline and we
assert side effects directly. No broker required.
"""

from __future__ import annotations

import os
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from modules.instruments.models import Instrument
from modules.integrations.veeva import tasks
from modules.integrations.veeva.models import IntegrationPushLog
from modules.measurements.models import Measurement
from modules.samples.models import Sample


def _make_measurement_setup():
    instrument = Instrument.objects.create(
        name="Mettler", instrument_type="Balance",
        serial_number="MT-CELERY-1", connection_type="RS232",
    )
    sample = Sample.objects.create(
        sample_id="SMP-CELERY-1", instrument=instrument,
        batch_number="B", created_by="lab",
    )
    return instrument, sample


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    VEEVA_INTEGRATION_ENABLED=False,  # disabled by default
    VEEVA_MODE="disabled",
)
class PushTaskDisabledTest(TestCase):
    """When the integration is off, the task is a no-op."""

    def test_no_op_when_disabled(self) -> None:
        instrument, sample = _make_measurement_setup()
        measurement = Measurement.objects.create(
            sample=sample, instrument=instrument,
            parameter="weight", value="1.0", unit="g",
            measured_at=timezone.now(),
        )
        baseline = IntegrationPushLog.objects.count()
        result = tasks.push_measurement_async.delay(measurement.pk).get()
        self.assertIsNone(result)
        # No log row created
        self.assertEqual(IntegrationPushLog.objects.count(), baseline)

    def test_no_op_when_measurement_missing(self) -> None:
        # Even if enabled, a missing measurement returns None gracefully
        with override_settings(VEEVA_INTEGRATION_ENABLED=True, VEEVA_MODE="mock"):
            result = tasks.push_measurement_async.delay(999_999).get()
        self.assertIsNone(result)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    VEEVA_INTEGRATION_ENABLED=True,
    VEEVA_MODE="mock",
    VEEVA_BASE_URL="http://localhost:8001/veeva",
    VEEVA_SHARED_SECRET="test-secret",
)
class PushTaskEnabledTest(TestCase):
    """When enabled, the task calls service.push_measurement."""

    def test_task_invokes_service_with_measurement(self) -> None:
        instrument, sample = _make_measurement_setup()
        measurement = Measurement.objects.create(
            sample=sample, instrument=instrument,
            parameter="weight", value="2.0", unit="g",
            measured_at=timezone.now(),
        )

        # Spy on the service rather than letting it open a network socket.
        fake_record = mock.Mock(
            pk=123,
            status=IntegrationPushLog.STATUS_SUCCESS,
            target_object_id="VV-MOCK-XYZ",
        )
        with mock.patch(
            "modules.integrations.veeva.service.push_measurement",
            return_value=fake_record,
        ) as spy:
            result = tasks.push_measurement_async.delay(measurement.pk).get()

        self.assertEqual(result, 123)
        spy.assert_called_once()
        # The measurement passed to the service is the one we created
        passed_measurement = spy.call_args.args[0]
        self.assertEqual(passed_measurement.pk, measurement.pk)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    VEEVA_INTEGRATION_ENABLED=True,
    VEEVA_MODE="mock",
)
class RetryFailedPushesTest(TestCase):
    def test_retry_finds_failed_jobs_and_requeues(self) -> None:
        # Insert two failed Veeva push log rows directly. We avoid the
        # measurement-creation signal path so no extra rows sneak in.
        for i, mid in enumerate((9001, 9002)):
            IntegrationPushLog.objects.create(
                vendor=IntegrationPushLog.VENDOR_VEEVA,
                target_object_type=IntegrationPushLog.TARGET_QUALITY_EVENT,
                source_measurement_id=mid,
                payload_hash=f"hash-{i}",
                status=IntegrationPushLog.STATUS_FAILED,
                mode=IntegrationPushLog.MODE_MOCK,
            )

        fake_record = mock.Mock(
            pk=0,
            status=IntegrationPushLog.STATUS_SUCCESS,
            target_object_id="VV-MOCK-XYZ",
        )
        with mock.patch(
            "modules.integrations.veeva.service.push_measurement",
            return_value=fake_record,
        ):
            result = tasks.retry_failed_pushes.delay().get()

        self.assertEqual(result["found"], 2)
        self.assertEqual(result["requeued"], 2)

    def test_retry_skips_non_veeva_vendors(self) -> None:
        # Insert an Empower-only failed log without going through the
        # Measurement signal path so no Veeva row is auto-created.
        IntegrationPushLog.objects.create(
            vendor=IntegrationPushLog.VENDOR_EMPOWER,  # not veeva
            target_object_type=IntegrationPushLog.TARGET_GENERIC_RESULT,
            source_measurement_id=999_001,  # synthetic
            payload_hash="hash-x",
            status=IntegrationPushLog.STATUS_FAILED,
            mode=IntegrationPushLog.MODE_MOCK,
        )
        result = tasks.retry_failed_pushes.delay().get()
        self.assertEqual(result["found"], 0)

    def test_retry_respects_batch_size(self) -> None:
        for i in range(5):
            IntegrationPushLog.objects.create(
                vendor=IntegrationPushLog.VENDOR_VEEVA,
                target_object_type=IntegrationPushLog.TARGET_QUALITY_EVENT,
                source_measurement_id=8000 + i,
                payload_hash=f"hash-{i}",
                status=IntegrationPushLog.STATUS_FAILED,
                mode=IntegrationPushLog.MODE_MOCK,
            )

        fake_record = mock.Mock(
            pk=0,
            status=IntegrationPushLog.STATUS_SUCCESS,
            target_object_id="VV-MOCK-XYZ",
        )
        with mock.patch.object(tasks, "RETRY_BATCH_SIZE", 2), \
                mock.patch(
                    "modules.integrations.veeva.service.push_measurement",
                    return_value=fake_record,
                ):
            result = tasks.retry_failed_pushes.delay().get()
        self.assertEqual(result["found"], 2)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    VEEVA_INTEGRATION_ENABLED=True,
    VEEVA_MODE="mock",
)
class SignalUsesCeleryWhenEnabledTest(TestCase):
    """post_save(Measurement) routes through the Celery task when async on."""

    def test_signal_uses_celery_when_async_push_enabled(self) -> None:
        instrument, sample = _make_measurement_setup()
        # The signal imports push_measurement_async LOCALLY at call time,
        # so we patch the source module (tasks). delay() is invoked via
        # the resolved Task object.
        with mock.patch.dict(os.environ, {"VEEVA_ASYNC_PUSH": "true"}, clear=False):
            with mock.patch.object(
                tasks.push_measurement_async, "delay",
                side_effect=lambda *a, **kw: None,
            ) as enqueue_spy:
                Measurement.objects.create(
                    sample=sample, instrument=instrument,
                    parameter="weight", value="1.0", unit="g",
                    measured_at=timezone.now(),
                )
        enqueue_spy.assert_called_once()

    def test_signal_inline_when_async_push_disabled(self) -> None:
        instrument, sample = _make_measurement_setup()
        with mock.patch.dict(os.environ, {"VEEVA_ASYNC_PUSH": "false"}, clear=False):
            with mock.patch.object(
                tasks.push_measurement_async, "delay",
            ) as enqueue_spy, mock.patch(
                "modules.integrations.veeva.service.push_measurement"
            ) as inline_spy:
                Measurement.objects.create(
                    sample=sample, instrument=instrument,
                    parameter="weight", value="1.0", unit="g",
                    measured_at=timezone.now(),
                )
        enqueue_spy.assert_not_called()
        inline_spy.assert_called_once()
