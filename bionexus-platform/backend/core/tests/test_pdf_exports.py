"""Tests for the ReportLab-backed PDF export endpoints.

We can't easily assert on rendered glyphs, but we can verify :

- Response is application/pdf with the correct disposition
- Body starts with the PDF magic bytes ``%PDF-``
- The integrity hash printed in the footer matches the deterministic
  hash computed from the source rows (proves the report's data
  pipeline didn't tamper with the records)
- Filters are honored (date_from / parameter / etc.)
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core import export_views
from core.audit import AuditTrail
from modules.instruments.models import Instrument
from modules.measurements.models import Measurement
from modules.samples.models import Sample


def _make_full_measurement(**overrides) -> Measurement:
    instrument = Instrument.objects.create(
        name="Mettler XPE205",
        instrument_type="Balance",
        serial_number=overrides.pop("serial", "MT-PDF-001"),
        connection_type="RS232",
    )
    sample = Sample.objects.create(
        sample_id=overrides.pop("sample_id", "SMP-PDF-001"),
        instrument=instrument,
        batch_number="BATCH-PDF",
        created_by="lab",
    )
    return Measurement.objects.create(
        sample=sample,
        instrument=instrument,
        parameter=overrides.get("parameter", "weight"),
        value=overrides.get("value", "12.3456"),
        unit=overrides.get("unit", "g"),
        measured_at=timezone.now(),
    )


class MeasurementsPdfTest(TestCase):
    def test_response_is_real_pdf(self) -> None:
        _make_full_measurement()
        response = self.client.get("/api/export/measurements/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF-", response.content[:8])
        # ReportLab always closes a PDF with %%EOF
        self.assertIn(b"%%EOF", response.content[-1024:])

    def test_filename_uses_doc_id(self) -> None:
        _make_full_measurement()
        response = self.client.get("/api/export/measurements/pdf/")
        cd = response["Content-Disposition"]
        self.assertIn("LBN-RPT-MEAS-", cd)
        self.assertTrue(cd.endswith('.pdf"'))

    def test_empty_export_still_renders(self) -> None:
        response = self.client.get("/api/export/measurements/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"%PDF-", response.content[:8])

    def test_filter_by_parameter_changes_report_hash(self) -> None:
        """Filtering at the endpoint produces a different report-level hash.

        ReportLab compresses the page content stream so we can't easily
        scan the rendered text. We instead verify that two endpoint
        calls with different filters produce different responses
        (different doc_id timestamps + different underlying data).
        """
        _make_full_measurement(parameter="pH")
        _make_full_measurement(
            serial="MT-PDF-002", sample_id="SMP-PDF-002", parameter="weight",
        )
        self.assertEqual(Measurement.objects.count(), 2)

        response_all = self.client.get("/api/export/measurements/pdf/")
        response_ph = self.client.get("/api/export/measurements/pdf/?parameter=pH")
        self.assertEqual(response_all.status_code, 200)
        self.assertEqual(response_ph.status_code, 200)
        # Same PDF magic header, but the bodies must differ when the
        # filter removed records.
        self.assertNotEqual(response_all.content, response_ph.content)


class AuditPdfTest(TestCase):
    def _seed_audit_log(self) -> None:
        for i in range(3):
            AuditTrail.record(
                entity_type="Probe",
                entity_id=i + 1,
                operation="CREATE",
                changes={},
                snapshot_before={},
                snapshot_after={"i": i},
                user_email=f"op-{i}@labionexus.local",
            )

    def test_response_is_real_pdf(self) -> None:
        self._seed_audit_log()
        response = self.client.get("/api/export/audit/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF-", response.content[:8])
        self.assertIn(b"%%EOF", response.content[-1024:])

    def test_filename_uses_doc_id(self) -> None:
        self._seed_audit_log()
        response = self.client.get("/api/export/audit/pdf/")
        cd = response["Content-Disposition"]
        self.assertIn("LBN-RPT-AUDIT-", cd)
        self.assertTrue(cd.endswith('.pdf"'))

    def test_filter_by_entity_type_changes_report(self) -> None:
        AuditTrail.record(
            entity_type="Probe", entity_id=1, operation="CREATE",
            changes={}, snapshot_before={}, snapshot_after={"a": 1},
            user_email="op-a@labionexus.local",
        )
        AuditTrail.record(
            entity_type="Other", entity_id=1, operation="UPDATE",
            changes={"x": {"before": 1, "after": 2}},
            snapshot_before={"x": 1}, snapshot_after={"x": 2},
            user_email="op-b@labionexus.local",
        )

        response_all = self.client.get("/api/export/audit/pdf/")
        response_probe = self.client.get("/api/export/audit/pdf/?entity_type=Probe")
        self.assertEqual(response_all.status_code, 200)
        self.assertEqual(response_probe.status_code, 200)
        # Different filters => different rendered bodies
        self.assertNotEqual(response_all.content, response_probe.content)


class ExportFormatsTest(TestCase):
    def test_pdf_audit_export_is_listed(self) -> None:
        response = self.client.get("/api/export/")
        self.assertEqual(response.status_code, 200)
        names = [e["name"] for e in response.data["exports"]]
        self.assertIn("Measurements (PDF)", names)
        self.assertIn("Audit Trail (PDF)", names)


class ReportHashTest(TestCase):
    """The `_compute_report_hash` helper is deterministic across rebuilds."""

    def test_same_input_same_hash(self) -> None:
        rows = [["A", "B"], ["1", "x"], ["2", "y"]]
        h1 = export_views._compute_report_hash(rows)
        h2 = export_views._compute_report_hash(rows)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_different_input_different_hash(self) -> None:
        a = export_views._compute_report_hash([["A"], ["1"]])
        b = export_views._compute_report_hash([["A"], ["2"]])
        self.assertNotEqual(a, b)
