"""End-to-end: Box parser -> metadata -> API -> DB -> audit trail.

This test exercises the full capture pipeline in one go:

    1. Raw instrument line (e.g., Mettler SICS "S S 12.3456 g")
       is fed through box_collector.parse_line() with a real
       CaptureContext (operator, lot, method).

    2. The resulting payload is sent to the composite API
       POST /api/measurements/ with nested context.

    3. The server-side serializer atomically creates a Measurement
       and a MeasurementContext, validating required fields from
       the InstrumentConfig.

    4. We assert the database state: Measurement row, MeasurementContext row,
       and the signals-driven AuditLog chain.

The test proves there are no gaps between the Box capture pipeline,
the API contract, the ORM, and the audit trail.
"""

import os
import sys
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import AuditLog
from modules.instruments.models import Instrument, InstrumentConfig
from modules.measurements.models import Measurement, MeasurementContext
from modules.samples.models import Sample

# Allow importing box_collector from the Box gateway side-by-side with
# the backend. The `box/` directory is outside the Django app tree, so
# we splice it onto sys.path just for these tests.
_BOX_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "box")
)
if _BOX_DIR not in sys.path:
    sys.path.insert(0, _BOX_DIR)

from box_collector import (  # noqa: E402
    CaptureContext,
    compute_capture_hash,
    parse_line,
)


class EndToEndCaptureTest(TestCase):
    """Full Box-to-audit pipeline in a single transaction."""

    def setUp(self) -> None:
        self.client = APIClient()

        self.instrument = Instrument.objects.create(
            name="Mettler XPE205",
            instrument_type="Balance",
            serial_number="MT-E2E-001",
            connection_type="RS232",
        )
        # Real InstrumentConfig with required metadata — mirrors a live QC lab.
        self.config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
            units="g",
            required_metadata_fields=["operator", "lot_number", "method"],
            thresholds={
                # Threshold target is the deviation %, not the raw weight.
                # Raw weights from a balance (12 g, 42 g, ...) would always
                # exceed a 1.0 "block" rule and prevent the E2E flow once
                # threshold enforcement is wired (LBN-CONF-002).
                "weight_deviation": {"warn": 0.5, "block": 1.0, "unit": "%"},
            },
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-E2E-001",
            instrument=self.instrument,
            batch_number="BATCH-E2E",
            created_by="lab_tech_e2e",
        )

    # -----------------------------------------------------------------
    # Step 1 — Box parser turns a raw line into a typed payload
    # -----------------------------------------------------------------
    def test_01_box_parser_produces_metadata_payload(self) -> None:
        """The parser pipeline must emit every field the API expects."""
        ctx = CaptureContext(
            instrument_id=self.instrument.pk,
            sample_id=self.sample.pk,
            operator="OP-042",
            lot_number="LOT-2026-04-23",
            method="USP <621>",
            external_sample_id="QC-SMP-100",
        )

        payload = parse_line("S S     12.3456 g", ctx)

        assert payload is not None, "Parser should recognize a valid SICS line"
        # Reading fields
        self.assertEqual(payload["parameter"], "weight")
        self.assertEqual(payload["value"], "12.3456")
        self.assertEqual(payload["unit"], "g")
        # Context is present and preserved
        self.assertEqual(payload["context"]["operator"], "OP-042")
        self.assertEqual(payload["context"]["lot_number"], "LOT-2026-04-23")
        self.assertEqual(payload["context"]["method"], "USP <621>")
        # Hash is 64 hex chars and covers the metadata
        self.assertEqual(len(payload["data_hash"]), 64)
        # Tampering with operator must flip the hash
        tampered_ctx = CaptureContext(
            instrument_id=ctx.instrument_id, sample_id=ctx.sample_id,
            operator="ROGUE", lot_number=ctx.lot_number, method=ctx.method,
        )
        from box_collector import ParsedReading
        reading = ParsedReading(
            parameter=payload["parameter"],
            value=payload["value"],
            unit=payload["unit"],
            source_timestamp=payload["source_timestamp"],
            raw=payload["raw"],
            protocol_meta={},
        )
        rogue_hash = compute_capture_hash(reading, tampered_ctx)
        self.assertNotEqual(payload["data_hash"], rogue_hash)

    # -----------------------------------------------------------------
    # Step 2 — Composite API accepts Measurement + context in one POST
    # -----------------------------------------------------------------
    def test_02_composite_api_creates_measurement_and_context(self) -> None:
        """POST /api/measurements/ with nested context in a single call."""
        api_payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "parameter": "weight",
            "value": "12.3456",
            "unit": "g",
            "measured_at": timezone.now().isoformat(),
            "context": {
                "operator": "OP-042",
                "lot_number": "LOT-2026-04-23",
                "method": "USP <621>",
                "sample_id": "QC-SMP-100",
                "notes": "Calibration weigh-in",
            },
        }

        response = self.client.post("/api/measurements/", api_payload, format="json")

        self.assertEqual(
            response.status_code, 201,
            f"Expected 201, got {response.status_code}: {response.content!r}",
        )
        # Measurement row exists with correct data
        measurement = Measurement.objects.get(pk=response.data["id"])
        self.assertEqual(measurement.parameter, "weight")
        self.assertEqual(measurement.value, Decimal("12.3456"))
        # MeasurementContext row exists and is linked
        context = MeasurementContext.objects.get(measurement=measurement)
        self.assertEqual(context.operator, "OP-042")
        self.assertEqual(context.lot_number, "LOT-2026-04-23")
        self.assertEqual(context.method, "USP <621>")
        # Response includes the nested context (GET shape)
        self.assertIn("context", response.data)
        self.assertEqual(response.data["context"]["operator"], "OP-042")

    # -----------------------------------------------------------------
    # Step 3 — Required metadata enforcement happens at the API boundary
    # -----------------------------------------------------------------
    def test_03_missing_required_metadata_rejected_by_api(self) -> None:
        """InstrumentConfig.required_metadata_fields is honoured by POST."""
        api_payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "parameter": "weight",
            "value": "12.3456",
            "unit": "g",
            "measured_at": timezone.now().isoformat(),
            "context": {
                "operator": "OP-042",
                # lot_number missing
                # method missing
            },
        }
        response = self.client.post("/api/measurements/", api_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("context", response.data)
        self.assertIn("lot_number", response.data["context"])
        self.assertIn("method", response.data["context"])
        # Nothing was created
        self.assertEqual(Measurement.objects.count(), 0)
        self.assertEqual(MeasurementContext.objects.count(), 0)

    # -----------------------------------------------------------------
    # Step 4 — Missing context block at all is also rejected
    # -----------------------------------------------------------------
    def test_04_no_context_at_all_rejected_when_required(self) -> None:
        """A measurement without any context should fail when fields are required."""
        api_payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "parameter": "weight",
            "value": "12.3456",
            "unit": "g",
            "measured_at": timezone.now().isoformat(),
        }
        response = self.client.post("/api/measurements/", api_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("context", response.data)

    # -----------------------------------------------------------------
    # Step 5 — Audit trail is populated by signals
    # -----------------------------------------------------------------
    def test_05_audit_trail_recorded_on_composite_create(self) -> None:
        """Creating via the composite endpoint writes the Measurement audit entry."""
        baseline = AuditLog.objects.filter(entity_type="Measurement").count()

        api_payload = {
            "sample": self.sample.pk,
            "instrument": self.instrument.pk,
            "parameter": "weight",
            "value": "12.3456",
            "unit": "g",
            "measured_at": timezone.now().isoformat(),
            "context": {
                "operator": "OP-042",
                "lot_number": "LOT-AUDIT",
                "method": "USP <621>",
            },
        }
        response = self.client.post("/api/measurements/", api_payload, format="json")
        self.assertEqual(response.status_code, 201)

        # Audit chain should have grown by exactly one Measurement CREATE record
        post_count = AuditLog.objects.filter(entity_type="Measurement").count()
        self.assertEqual(post_count, baseline + 1)
        latest = AuditLog.objects.filter(entity_type="Measurement").latest("timestamp")
        self.assertEqual(latest.operation, "CREATE")
        self.assertEqual(latest.entity_id, response.data["id"])

    # -----------------------------------------------------------------
    # Step 6 — GET /api/instruments/{id}/config/ drives the frontend
    # -----------------------------------------------------------------
    def test_06_instrument_config_endpoint_exposes_required_fields(self) -> None:
        response = self.client.get(f"/api/instruments/{self.instrument.pk}/config/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["configured"])
        self.assertEqual(response.data["parser_type"], "mettler_sics_v1")
        self.assertEqual(response.data["units"], "g")
        self.assertEqual(
            response.data["required_metadata_fields"],
            ["operator", "lot_number", "method"],
        )

    def test_07_instrument_config_endpoint_handles_unconfigured(self) -> None:
        """An instrument without a config still returns a usable response."""
        bare = Instrument.objects.create(
            name="Bare Instrument",
            instrument_type="pH Meter",
            serial_number="BARE-001",
            connection_type="USB",
        )
        response = self.client.get(f"/api/instruments/{bare.pk}/config/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["configured"])
        self.assertEqual(response.data["required_metadata_fields"], [])

    # -----------------------------------------------------------------
    # Step 8 — Full round-trip: Box payload -> composite API -> DB
    # -----------------------------------------------------------------
    def test_08_box_payload_feeds_composite_api(self) -> None:
        """The same payload the Box would emit can drive the composite API.

        This is the critical glue test: it proves the Box and the API
        speak the same shape for metadata-bearing captures.
        """
        ctx = CaptureContext(
            instrument_id=self.instrument.pk,
            sample_id=self.sample.pk,
            operator="OP-042",
            lot_number="LOT-ROUND-TRIP",
            method="USP <621>",
        )
        box_payload = parse_line("S S     42.0000 g", ctx)
        self.assertIsNotNone(box_payload)

        # Transform the Box payload into the composite API shape
        api_payload = {
            "sample": box_payload["sample_id"],
            "instrument": box_payload["instrument_id"],
            "parameter": box_payload["parameter"],
            "value": box_payload["value"],
            "unit": box_payload["unit"],
            "measured_at": box_payload["source_timestamp"],
            "context": {
                "operator": box_payload["context"]["operator"],
                "lot_number": box_payload["context"]["lot_number"],
                "method": box_payload["context"]["method"],
                "sample_id": box_payload["context"].get("sample_id", ""),
                "notes": box_payload["context"].get("notes", ""),
            },
        }

        response = self.client.post("/api/measurements/", api_payload, format="json")
        self.assertEqual(response.status_code, 201)

        measurement = Measurement.objects.get(pk=response.data["id"])
        self.assertEqual(measurement.value, Decimal("42.0000"))
        ctx_row = MeasurementContext.objects.get(measurement=measurement)
        self.assertEqual(ctx_row.operator, "OP-042")
        self.assertEqual(ctx_row.lot_number, "LOT-ROUND-TRIP")
