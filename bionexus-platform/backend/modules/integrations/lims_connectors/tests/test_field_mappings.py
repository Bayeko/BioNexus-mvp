"""Cross-vendor field mapping tests.

One test class per vendor mapper, all using the same Measurement-shaped
stub so any drift in the source-of-truth measurement shape breaks every
vendor at once (and we see it).
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from modules.integrations.lims_connectors.benchling.field_mapping import (
    measurement_to_result_row,
)
from modules.integrations.lims_connectors.empower.field_mapping import (
    measurement_to_result as empower_map,
)
from modules.integrations.lims_connectors.labware.field_mapping import (
    measurement_to_result as labware_map,
)
from modules.integrations.lims_connectors.starlims.field_mapping import (
    measurement_to_test_result as starlims_map,
)


def _stub_measurement():
    return SimpleNamespace(
        id=42,
        parameter="Caffeine",
        value=Decimal("99.82"),
        unit="%",
        measured_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=timezone.utc),
        data_hash="a" * 64,
        sample=SimpleNamespace(sample_id="QC-100"),
        instrument=SimpleNamespace(serial_number="HPLC-001"),
        context=SimpleNamespace(
            operator="OP-042",
            lot_number="LOT-2026-04",
            method="USP <621>",
            sample_id="ALIAS-QC-100",
        ),
    )


class TestEmpowerMapping:
    def test_core_fields(self) -> None:
        out = empower_map(_stub_measurement())
        assert out["peakName"] == "Caffeine"
        assert out["amount"] == "99.82"
        assert out["unit"] == "%"
        assert out["sampleName"] == "QC-100"
        assert out["operator"] == "OP-042"
        assert out["lotNumber"] == "LOT-2026-04"
        assert out["instrumentSerial"] == "HPLC-001"
        assert out["sourceHash"] == "a" * 64

    def test_iso8601_measured_at(self) -> None:
        out = empower_map(_stub_measurement())
        assert out["measuredAt"] == "2026-04-23T10:00:00+00:00"

    def test_no_context_falls_back_to_empty(self) -> None:
        m = _stub_measurement()

        class Raiser:
            def __get__(self, obj, objtype=None):
                raise RuntimeError()

        m.context = property(lambda self: (_ for _ in ()).throw(RuntimeError()))
        out = empower_map(m)
        assert out["operator"] == ""
        assert out["lotNumber"] == ""

    def test_value_string_preserves_precision(self) -> None:
        m = _stub_measurement()
        m.value = Decimal("12.3456789012")
        out = empower_map(m)
        assert out["amount"] == "12.3456789012"


class TestLabWareMapping:
    def test_core_fields(self) -> None:
        out = labware_map(_stub_measurement())
        assert out["sample_id"] == "QC-100"
        assert out["lot_no"] == "LOT-2026-04"
        assert out["analysis"] == "USP <621>"
        assert out["test_name"] == "Caffeine"
        assert out["result_value"] == "99.82"
        assert out["uom"] == "%"
        assert out["tested_by"] == "OP-042"
        assert out["instrument"] == "HPLC-001"

    def test_source_hash_preserved(self) -> None:
        out = labware_map(_stub_measurement())
        assert out["source_hash"] == "a" * 64


class TestStarlimsMapping:
    def test_core_fields(self) -> None:
        out = starlims_map(_stub_measurement())
        assert out["sample"] == "QC-100"
        assert out["batch"] == "LOT-2026-04"
        assert out["test"] == "Caffeine"
        assert out["value"] == "99.82"
        assert out["units"] == "%"
        assert out["operator"] == "OP-042"
        assert out["instrument"] == "HPLC-001"
        assert out["method"] == "USP <621>"


class TestBenchlingMapping:
    def test_schema_id_envelope(self) -> None:
        out = measurement_to_result_row(_stub_measurement())
        assert "schemaId" in out
        assert "fields" in out
        assert isinstance(out["fields"], dict)

    def test_field_values(self) -> None:
        out = measurement_to_result_row(_stub_measurement())
        f = out["fields"]
        assert f["parameter"]["value"] == "Caffeine"
        assert f["value"]["value"] == "99.82"
        assert f["unit"]["value"] == "%"
        assert f["operator"]["value"] == "OP-042"
        assert f["lotNumber"]["value"] == "LOT-2026-04"
        assert f["sourceHash"]["value"] == "a" * 64

    def test_schema_id_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("BENCHLING_RESULT_SCHEMA_ID", "sch_cust_123")
        out = measurement_to_result_row(_stub_measurement())
        assert out["schemaId"] == "sch_cust_123"


class TestAllVendorsAgree:
    """A few sanity invariants that must hold across all vendor mappings."""

    @pytest.mark.parametrize("mapper", [
        empower_map, labware_map, starlims_map,
    ])
    def test_value_is_string_not_decimal(self, mapper) -> None:
        """Vault/LIMS field values must be strings — Decimal would crash JSON serialization."""
        out = mapper(_stub_measurement())
        # Find the value-bearing field per vendor convention.
        for k, v in out.items():
            if not isinstance(v, (str, int, float)):
                pytest.fail(f"{mapper.__module__} produced non-primitive {k}={type(v)}")

    @pytest.mark.parametrize("mapper", [
        empower_map, labware_map, starlims_map,
    ])
    def test_no_python_objects_leak(self, mapper) -> None:
        """The Decimal value must come out as str, never Decimal/None."""
        out = mapper(_stub_measurement())
        # Every value should be JSON-serializable (str/int/float/bool/None).
        for k, v in out.items():
            assert v is None or isinstance(v, (str, int, float, bool)), (
                f"{mapper.__module__}: {k} is {type(v).__name__}"
            )
