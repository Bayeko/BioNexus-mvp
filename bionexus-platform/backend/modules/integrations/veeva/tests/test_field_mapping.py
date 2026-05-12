"""Tests for the BioNexus → Vault field mapping.

These pin the spec mapping so any regulatory regression breaks loudly.
Uses lightweight stubs rather than the Django ORM to keep these as pure
unit tests with zero DB cost.
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from modules.integrations.veeva.field_mapping import (
    measurement_to_quality_event,
    report_to_document,
)


def _measurement(**overrides):
    """Build a Measurement-shaped stub with the fields the mapping reads."""
    defaults = dict(
        parameter="pH",
        value=Decimal("7.42"),
        unit="pH",
        measured_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=timezone.utc),
        data_hash="a" * 64,
        sample=SimpleNamespace(barcode="QC-100"),
        instrument=SimpleNamespace(serial_number="HPLC-001"),
        context=SimpleNamespace(
            operator="OP-042",
            lot_number="LOT-2026-04",
            method="USP <621>",
            sample_id="ALIAS-QC-100",
        ),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _report(**overrides):
    defaults = dict(
        id=42,
        title="QC Release Report — Lot LOT-2026-04",
        signed_by="qp.dupont@lbn.ch",
        signed_at=datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc),
        signature_hash="b" * 64,
        tenant=SimpleNamespace(name="Lab BioNexus AG"),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestMeasurementToQualityEvent:
    def test_all_spec_fields_present(self) -> None:
        out = measurement_to_quality_event(_measurement())
        expected_fields = {
            "parameter__v",
            "value__v",
            "unit__v",
            "measured_at__v",
            "source_hash__v",
            "sample_external_id__v",
            "reported_by__v",
            "lot__v",
            "method__v",
            "sample_alias__v",
            "instrument__v",
        }
        assert set(out.keys()) == expected_fields, (
            f"Unexpected fields: {set(out.keys()) ^ expected_fields}"
        )

    def test_core_values_mapped(self) -> None:
        out = measurement_to_quality_event(_measurement())
        assert out["parameter__v"] == "pH"
        assert out["value__v"] == "7.42"  # string form preserves precision
        assert out["unit__v"] == "pH"
        assert out["source_hash__v"] == "a" * 64

    def test_iso_8601_measured_at(self) -> None:
        out = measurement_to_quality_event(_measurement())
        assert out["measured_at__v"] == "2026-04-23T10:00:00+00:00"

    def test_context_fields_mapped(self) -> None:
        out = measurement_to_quality_event(_measurement())
        assert out["reported_by__v"] == "OP-042"
        assert out["lot__v"] == "LOT-2026-04"
        assert out["method__v"] == "USP <621>"
        assert out["sample_alias__v"] == "ALIAS-QC-100"

    def test_instrument_provenance(self) -> None:
        out = measurement_to_quality_event(_measurement())
        assert out["instrument__v"] == "HPLC-001"

    def test_sample_external_id_from_barcode(self) -> None:
        out = measurement_to_quality_event(_measurement())
        assert out["sample_external_id__v"] == "QC-100"

    def test_missing_context_falls_back_to_empty_strings(self) -> None:
        m = _measurement()
        # Simulate ORM DoesNotExist by raising on attribute access.
        class Raiser:
            def __get__(self, obj, objtype=None):
                raise RuntimeError("DoesNotExist")
        m.context = property(lambda self: (_ for _ in ()).throw(RuntimeError()))
        # The mapping uses getattr/try-except so this should still produce a dict
        # with empty strings for the optional fields.
        out = measurement_to_quality_event(m)
        assert out["reported_by__v"] == ""
        assert out["lot__v"] == ""
        assert out["method__v"] == ""
        assert out["sample_alias__v"] == ""

    def test_missing_optional_strings_become_empty(self) -> None:
        m = _measurement(
            context=SimpleNamespace(
                operator="", lot_number="", method="", sample_id=""
            ),
            sample=SimpleNamespace(barcode=""),
            instrument=SimpleNamespace(serial_number=""),
        )
        out = measurement_to_quality_event(m)
        assert out["reported_by__v"] == ""
        assert out["lot__v"] == ""
        assert out["sample_external_id__v"] == ""
        assert out["instrument__v"] == ""

    def test_value_string_form_preserves_precision(self) -> None:
        """Decimal -> str must not silently round."""
        m = _measurement(value=Decimal("12.3456789012"))
        out = measurement_to_quality_event(m)
        assert out["value__v"] == "12.3456789012"

    def test_no_extra_keys_leak(self) -> None:
        """Vault rejects extra fields — make sure nothing else slips in."""
        m = _measurement()
        # Decorate stub with extra attributes that the mapping must not pick up.
        m.debug_field = "should not appear"
        m.internal_note = "neither this"
        out = measurement_to_quality_event(m)
        assert "debug_field" not in out
        assert "internal_note" not in out


class TestReportToDocument:
    def test_all_fields_mapped(self) -> None:
        out = report_to_document(_report())
        assert out["external_id__v"] == "BNX-RPT-42"
        assert out["name__v"] == "QC Release Report — Lot LOT-2026-04"
        assert out["signed_by__v"] == "qp.dupont@lbn.ch"
        assert out["signed_at__v"] == "2026-04-23T12:00:00+00:00"
        assert out["signature_hash__v"] == "b" * 64
        assert out["source_system__v"] == "Lab BioNexus AG"

    def test_default_name_when_title_missing(self) -> None:
        r = _report(title="")
        out = report_to_document(r)
        assert out["name__v"] == "BioNexus Certified Report #42"

    def test_default_source_system(self) -> None:
        r = _report(tenant=SimpleNamespace(name=""))
        out = report_to_document(r)
        assert out["source_system__v"] == "BioNexus"
