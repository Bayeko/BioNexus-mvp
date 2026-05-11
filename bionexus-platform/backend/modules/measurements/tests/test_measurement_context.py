"""Tests for MeasurementContext model and API.

Covers:
- Model creation and field defaults
- OneToOne relationship with Measurement
- API CRUD (happy path + errors)
- Required metadata field enforcement via InstrumentConfig
- Filtering by operator, lot_number, instrument
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.instruments.models import Instrument, InstrumentConfig
from modules.measurements.models import Measurement, MeasurementContext
from modules.samples.models import Sample


class MeasurementContextModelTest(TestCase):
    """Unit tests for the MeasurementContext model."""

    def setUp(self) -> None:
        self.instrument = Instrument.objects.create(
            name="Mettler XPE205",
            instrument_type="Balance",
            serial_number="MT-CTX-001",
            connection_type="RS232",
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-CTX-001",
            instrument=self.instrument,
            batch_number="BATCH-CTX-1",
            created_by="lab_tech_1",
        )
        self.measurement = Measurement.objects.create(
            sample=self.sample,
            instrument=self.instrument,
            parameter="weight",
            value="12.3456000000",
            unit="g",
            measured_at=timezone.now(),
        )

    def test_create_context_with_all_fields(self) -> None:
        ctx = MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-042",
            lot_number="LOT-2026-04",
            method="USP <621>",
            sample_id="EXT-SMP-001",
            notes="Routine weighing check",
        )
        self.assertEqual(ctx.operator, "OP-042")
        self.assertEqual(ctx.lot_number, "LOT-2026-04")
        self.assertEqual(ctx.method, "USP <621>")
        self.assertEqual(ctx.sample_id, "EXT-SMP-001")
        self.assertIsNotNone(ctx.timestamp)

    def test_create_context_minimal(self) -> None:
        """All text fields are optional at the DB level."""
        ctx = MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
        )
        self.assertEqual(ctx.operator, "")
        self.assertEqual(ctx.lot_number, "")
        self.assertIsNotNone(ctx.pk)

    def test_one_to_one_enforcement(self) -> None:
        """Only one context per measurement."""
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-001",
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            MeasurementContext.objects.create(
                measurement=self.measurement,
                instrument=self.instrument,
                operator="OP-002",
            )

    def test_cascade_delete(self) -> None:
        """Deleting a measurement cascades to its context."""
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-001",
        )
        self.assertEqual(MeasurementContext.objects.count(), 1)
        self.measurement.delete()
        self.assertEqual(MeasurementContext.objects.count(), 0)

    def test_instrument_protect(self) -> None:
        """Cannot delete an instrument that has contexts (PROTECT)."""
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-001",
        )
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.instrument.delete()

    def test_str_representation(self) -> None:
        ctx = MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-042",
            lot_number="LOT-99",
            method="Ph.Eur.2.2.25",
        )
        s = str(ctx)
        self.assertIn("OP-042", s)
        self.assertIn("LOT-99", s)
        self.assertIn("Ph.Eur.2.2.25", s)

    def test_reverse_access_from_measurement(self) -> None:
        """Measurement.context returns the attached context."""
        ctx = MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-042",
        )
        self.assertEqual(self.measurement.context, ctx)


class MeasurementContextAPITest(TestCase):
    """Integration tests for MeasurementContext API endpoints."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.instrument = Instrument.objects.create(
            name="Sartorius Quintix",
            instrument_type="Balance",
            serial_number="SAR-CTX-001",
            connection_type="USB",
        )
        self.sample = Sample.objects.create(
            sample_id="SMP-API-CTX",
            instrument=self.instrument,
            batch_number="BATCH-API",
            created_by="lab_tech_2",
        )
        self.measurement = Measurement.objects.create(
            sample=self.sample,
            instrument=self.instrument,
            parameter="weight",
            value="50.1230000000",
            unit="g",
            measured_at=timezone.now(),
        )

    def test_create_context_via_api(self) -> None:
        payload = {
            "measurement": self.measurement.pk,
            "instrument": self.instrument.pk,
            "operator": "OP-007",
            "lot_number": "LOT-2026-04-22",
            "method": "USP <621>",
            "sample_id": "QC-SMP-100",
            "notes": "Morning calibration check",
        }
        response = self.client.post(
            "/api/measurement-contexts/", payload, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["operator"], "OP-007")
        self.assertEqual(response.data["lot_number"], "LOT-2026-04-22")

    def test_list_contexts(self) -> None:
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-001",
        )
        response = self.client.get("/api/measurement-contexts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_operator(self) -> None:
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-FILTER",
        )
        response = self.client.get("/api/measurement-contexts/?operator=OP-FILTER")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.get("/api/measurement-contexts/?operator=OP-NONE")
        self.assertEqual(len(response.data), 0)

    def test_filter_by_lot_number(self) -> None:
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            lot_number="LOT-FILTER-01",
        )
        response = self.client.get(
            "/api/measurement-contexts/?lot_number=LOT-FILTER-01"
        )
        self.assertEqual(len(response.data), 1)

    def test_measurement_includes_context(self) -> None:
        """GET /api/measurements/{id}/ includes nested context."""
        MeasurementContext.objects.create(
            measurement=self.measurement,
            instrument=self.instrument,
            operator="OP-NESTED",
            lot_number="LOT-NESTED",
        )
        response = self.client.get(f"/api/measurements/{self.measurement.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("context", response.data)
        self.assertEqual(response.data["context"]["operator"], "OP-NESTED")

    def test_required_metadata_enforcement(self) -> None:
        """When InstrumentConfig requires fields, API rejects incomplete contexts."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="sartorius_sbi_v1",
            units="g",
            required_metadata_fields=["operator", "lot_number"],
        )
        # Missing operator and lot_number
        payload = {
            "measurement": self.measurement.pk,
            "instrument": self.instrument.pk,
            "method": "USP <621>",
        }
        response = self.client.post(
            "/api/measurement-contexts/", payload, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("operator", response.data)
        self.assertIn("lot_number", response.data)

    def test_required_metadata_passes_when_provided(self) -> None:
        """When required fields are filled, context is accepted."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="sartorius_sbi_v1",
            units="g",
            required_metadata_fields=["operator", "lot_number"],
        )
        payload = {
            "measurement": self.measurement.pk,
            "instrument": self.instrument.pk,
            "operator": "OP-VALID",
            "lot_number": "LOT-VALID",
        }
        response = self.client.post(
            "/api/measurement-contexts/", payload, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_create_context_missing_measurement_fails(self) -> None:
        response = self.client.post(
            "/api/measurement-contexts/",
            {"instrument": self.instrument.pk, "operator": "OP-001"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
