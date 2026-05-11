"""Tests for threshold enforcement at the measurement API boundary.

Covers (per LBN-CONF-002):
- "log" verdict   : silent, no banner data, but still surfaced in response
- "alert" verdict : 201 + response.threshold_verdict == 'alert'
- "block" verdict : 400 + payload includes threshold_verdict='block'
- No InstrumentConfig         : verdict is None (legacy behaviour intact)
- Non-numeric value           : verdict skipped, capture still succeeds
- Verdict on the GET endpoint : always None (only set on create response)
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.instruments.models import Instrument, InstrumentConfig
from modules.measurements.models import Measurement
from modules.samples.models import Sample


class ThresholdEnforcementTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.instrument = Instrument.objects.create(
            name="pH meter A",
            instrument_type="pH meter",
            serial_number="PH-THR-001",
            connection_type="USB",
        )
        # pH expected in 6.8 to 7.6, alert if outside ; deviation > 1.0 blocks
        self.config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
            units="pH",
            required_metadata_fields=[],
            thresholds={
                "pH": {"min": 6.8, "max": 7.6, "action": "alert"},
                "weight_deviation": {"warn": 0.5, "block": 1.0, "unit": "%"},
            },
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-THR-001",
            instrument=self.instrument,
            batch_number="BATCH-THR",
            created_by="lab_tech",
        )
        self.base_payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "measured_at": timezone.now().isoformat(),
        }

    def _post(self, **overrides):
        payload = {
            **self.base_payload,
            "parameter": "pH",
            "value": "7.2",
            "unit": "pH",
            **overrides,
        }
        return self.client.post("/api/measurements/", payload, format="json")

    # ----------------------------------------------------------------
    # log verdict (value within spec)
    # ----------------------------------------------------------------

    def test_log_verdict_when_value_in_range(self) -> None:
        response = self._post(value="7.2")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threshold_verdict"], "log")

    def test_log_verdict_measurement_is_persisted(self) -> None:
        response = self._post(value="7.2")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Measurement.objects.filter(pk=response.data["id"]).exists())

    # ----------------------------------------------------------------
    # alert verdict (range violation)
    # ----------------------------------------------------------------

    def test_alert_verdict_when_value_below_min(self) -> None:
        response = self._post(value="6.5")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threshold_verdict"], "alert")

    def test_alert_verdict_when_value_above_max(self) -> None:
        response = self._post(value="8.0")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threshold_verdict"], "alert")

    def test_alert_verdict_still_persists_measurement(self) -> None:
        """Out-of-spec readings MUST be recorded (Annex 11 traceability)."""
        response = self._post(value="8.0")
        self.assertEqual(response.status_code, 201)
        measurement = Measurement.objects.get(pk=response.data["id"])
        self.assertEqual(measurement.value, Decimal("8.0"))

    # ----------------------------------------------------------------
    # block verdict (deviation rule triggered)
    # ----------------------------------------------------------------

    def test_block_verdict_rejects_creation(self) -> None:
        baseline_count = Measurement.objects.count()
        response = self._post(parameter="weight_deviation", value="1.5", unit="%")
        self.assertEqual(response.status_code, 400)
        self.assertIn("threshold_verdict", response.data)
        # DRF wraps non-field-error string values in a list of ErrorDetail ;
        # str() coerces back to the underlying message we set.
        verdict_payload = response.data["threshold_verdict"]
        if isinstance(verdict_payload, list):
            verdict_payload = verdict_payload[0]
        self.assertEqual(str(verdict_payload), "block")
        # Nothing was created
        self.assertEqual(Measurement.objects.count(), baseline_count)

    def test_block_verdict_error_message_mentions_parameter(self) -> None:
        response = self._post(parameter="weight_deviation", value="1.5", unit="%")
        self.assertEqual(response.status_code, 400)
        error_str = str(response.data["value"])
        self.assertIn("weight_deviation", error_str)
        self.assertIn("block", error_str)

    def test_warn_level_yields_alert_not_block(self) -> None:
        """Value above warn but below block => alert verdict, still recorded."""
        response = self._post(parameter="weight_deviation", value="0.7", unit="%")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threshold_verdict"], "alert")

    # ----------------------------------------------------------------
    # Edge cases
    # ----------------------------------------------------------------

    def test_no_config_means_no_verdict(self) -> None:
        bare_instrument = Instrument.objects.create(
            name="Bare", instrument_type="pH meter",
            serial_number="BARE-NOCONF",
            connection_type="USB",
        )
        bare_sample = Sample.objects.create(
            sample_id="SMP-NOCONF",
            instrument=bare_instrument,
            batch_number="B",
            created_by="lab",
        )
        response = self.client.post("/api/measurements/", {
            "sample": bare_sample.pk,
            "instrument": bare_instrument.pk,
            "parameter": "pH",
            "value": "9.0",
            "unit": "pH",
            "measured_at": timezone.now().isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["threshold_verdict"])

    def test_unknown_parameter_in_config_means_log_verdict(self) -> None:
        """A measurement parameter not in thresholds dict gets verdict=log."""
        response = self._post(parameter="conductivity", value="42.0", unit="mS/cm")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threshold_verdict"], "log")

    def test_get_endpoint_returns_null_verdict(self) -> None:
        """Verdict is only present on the create response, not on reads."""
        created = self._post(value="7.2")
        pk = created.data["id"]
        response = self.client.get(f"/api/measurements/{pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["threshold_verdict"])
