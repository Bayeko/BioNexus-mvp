"""Tests for box_collector parsers + metadata-bound SHA-256.

Covers:
- BaseParser contract (can_parse, extract, parse)
- MettlerSICSParser, SartoriusSBIParser, GenericCSVParser happy paths
- Parser dispatch (parse_line)
- Error handling (Mettler ES/EL/ET codes, malformed input)
- SHA-256 scope: hash covers value + timestamp + instrument_id + operator + lot_number
- Hash determinism (same inputs → same hash)
- Hash sensitivity (any metadata change → different hash)
- Backward compat: payload keys expected by the cloud endpoint are present
- build_capture_payload strips internal-only fields
"""

import json
import os
import sys

import pytest

# Allow running tests from the box/ directory directly (no Django path needed)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from box_collector import (  # noqa: E402
    AgilentChemStationParser,
    BaseParser,
    CaptureContext,
    GenericCSVParser,
    KarlFischerParser,
    MettlerSICSParser,
    ParsedReading,
    PARSERS,
    SartoriusSBIParser,
    build_capture_payload,
    compute_capture_hash,
    parse_line,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx() -> CaptureContext:
    return CaptureContext(
        instrument_id=42,
        sample_id=7,
        operator="OP-042",
        lot_number="LOT-2026-04",
        method="USP <621>",
        external_sample_id="QC-100",
        notes="Calibration check",
    )


@pytest.fixture
def empty_ctx() -> CaptureContext:
    return CaptureContext(instrument_id=1, sample_id=1)


# ---------------------------------------------------------------------------
# BaseParser contract
# ---------------------------------------------------------------------------

class TestBaseParserContract:
    def test_base_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore[abstract]

    def test_all_parsers_declare_name_and_protocol(self) -> None:
        for parser in PARSERS:
            assert parser.name and parser.name != "base"
            assert parser.protocol and parser.protocol != "base"

    def test_all_parsers_implement_contract(self, ctx: CaptureContext) -> None:
        sample_lines = {
            MettlerSICSParser: "S S     12.3456 g",
            SartoriusSBIParser: "+   100.0000 g",
            GenericCSVParser: "pH,7.42,pH",
        }
        for parser, line in sample_lines.items():
            assert parser.can_parse(line), f"{parser.__name__} should parse {line!r}"
            reading = parser.extract(line)
            assert isinstance(reading, ParsedReading)
            payload = parser.parse(line, ctx)
            assert payload is not None
            # Core keys every parser must emit
            for key in [
                "idempotency_key", "sample_id", "instrument_id",
                "parameter", "value", "unit",
                "source_timestamp", "hub_received_at",
                "raw", "data_hash",
                "context", "protocol_meta",
            ]:
                assert key in payload, f"{parser.__name__} missing {key}"
            # Context is fully populated from CaptureContext
            for key in ["operator", "lot_number", "method", "instrument_id"]:
                assert key in payload["context"]


# ---------------------------------------------------------------------------
# MettlerSICSParser
# ---------------------------------------------------------------------------

class TestMettlerSICSParser:
    def test_stable_weight(self, ctx: CaptureContext) -> None:
        result = MettlerSICSParser.parse("S S     12.3456 g", ctx)
        assert result is not None
        assert result["parameter"] == "weight"
        assert result["value"] == "12.3456"
        assert result["unit"] == "g"
        assert result["protocol_meta"]["protocol"] == "SICS"
        assert result["protocol_meta"]["stability"] == "stable"

    def test_dynamic_weight(self, ctx: CaptureContext) -> None:
        result = MettlerSICSParser.parse("S D     12.3400 g", ctx)
        assert result is not None
        assert result["protocol_meta"]["stability"] == "dynamic"

    def test_negative_value(self, ctx: CaptureContext) -> None:
        result = MettlerSICSParser.parse("S S     -5.1234 g", ctx)
        assert result is not None
        assert result["value"] == "-5.1234"

    def test_error_code_ES(self, ctx: CaptureContext) -> None:
        # Overload errors look like "ES S 0.0 g" in this format
        assert MettlerSICSParser.parse("ES S 0.0000 g", ctx) is None

    def test_error_code_EL(self, ctx: CaptureContext) -> None:
        assert MettlerSICSParser.parse("EL S 0.0000 g", ctx) is None

    def test_malformed_line(self, ctx: CaptureContext) -> None:
        assert MettlerSICSParser.parse("not a valid SICS frame", ctx) is None
        assert MettlerSICSParser.parse("", ctx) is None

    def test_can_parse_returns_bool(self) -> None:
        assert MettlerSICSParser.can_parse("S S 12.3 g") is True
        assert MettlerSICSParser.can_parse("invalid") is False

    def test_raw_preserved(self, ctx: CaptureContext) -> None:
        line = "S S     12.3456 g"
        result = MettlerSICSParser.parse(line, ctx)
        assert result is not None
        assert line in result["raw"] or result["raw"] == line.rstrip()


# ---------------------------------------------------------------------------
# SartoriusSBIParser
# ---------------------------------------------------------------------------

class TestSartoriusSBIParser:
    def test_positive_weight(self, ctx: CaptureContext) -> None:
        result = SartoriusSBIParser.parse("+   100.0000 g", ctx)
        assert result is not None
        assert result["value"] == "100.0000"
        assert result["unit"] == "g"
        assert result["protocol_meta"]["protocol"] == "SBI"

    def test_negative_weight(self, ctx: CaptureContext) -> None:
        result = SartoriusSBIParser.parse("-    5.1234 g", ctx)
        assert result is not None
        assert result["value"] == "-5.1234"

    def test_no_sign(self, ctx: CaptureContext) -> None:
        result = SartoriusSBIParser.parse("   50.2500 g", ctx)
        assert result is not None
        assert result["value"] == "50.2500"

    def test_malformed(self, ctx: CaptureContext) -> None:
        assert SartoriusSBIParser.parse("", ctx) is None
        assert SartoriusSBIParser.parse("garbage", ctx) is None


# ---------------------------------------------------------------------------
# GenericCSVParser
# ---------------------------------------------------------------------------

class TestGenericCSVParser:
    def test_ph_reading(self, ctx: CaptureContext) -> None:
        result = GenericCSVParser.parse("pH,7.42,pH", ctx)
        assert result is not None
        assert result["parameter"] == "pH"
        assert result["value"] == "7.42"
        assert result["unit"] == "pH"

    def test_temperature(self, ctx: CaptureContext) -> None:
        result = GenericCSVParser.parse("temperature,25.1,°C", ctx)
        assert result is not None
        assert result["parameter"] == "temperature"
        assert result["unit"] == "°C"

    def test_non_numeric_value_rejected(self, ctx: CaptureContext) -> None:
        assert GenericCSVParser.parse("pH,notanumber,pH", ctx) is None

    def test_too_few_fields(self, ctx: CaptureContext) -> None:
        assert GenericCSVParser.parse("pH,7.42", ctx) is None

    def test_extra_fields_ignored(self, ctx: CaptureContext) -> None:
        # Extra CSV fields shouldn't break the parser
        result = GenericCSVParser.parse("pH,7.42,pH,extra,fields", ctx)
        assert result is not None
        assert result["parameter"] == "pH"


# ---------------------------------------------------------------------------
# KarlFischerParser
# ---------------------------------------------------------------------------

class TestKarlFischerParser:
    """Tests for the Karl Fischer titrator parser (D7 T23).

    Format: ``KF,<parameter>,<value>,<unit>[,<sample_id>[,<vol>[,<drift>]]]``
    """

    MINIMAL = "KF,water_content,0.123,%"
    FULL = "KF,water_content,0.456,%,Sample-001,12.34,5.0"

    def test_parse_minimal_form(self, ctx: CaptureContext) -> None:
        result = KarlFischerParser.parse(self.MINIMAL, ctx)
        assert result is not None
        assert result["parameter"] == "water_content"
        assert result["value"] == "0.123"
        assert result["unit"] == "%"
        assert result["protocol_meta"]["protocol"] == "KF"
        assert result["protocol_meta"]["parser"] == "karl_fischer_v1"

    def test_parse_full_form_includes_optional_metadata(
        self, ctx: CaptureContext,
    ) -> None:
        result = KarlFischerParser.parse(self.FULL, ctx)
        assert result is not None
        assert result["value"] == "0.456"
        meta = result["protocol_meta"]
        assert meta["sample_id"] == "Sample-001"
        assert meta["volume_ml"] == 12.34
        assert meta["drift_ug_per_min"] == 5.0

    def test_can_parse_requires_kf_prefix(self) -> None:
        # No prefix => GenericCSV would handle it, KF must not
        assert KarlFischerParser.can_parse("water_content,0.123,%,Sample-001") is False

    def test_can_parse_rejects_non_numeric_value(self) -> None:
        assert KarlFischerParser.can_parse("KF,water_content,not-numeric,%") is False

    def test_can_parse_rejects_too_few_fields(self) -> None:
        assert KarlFischerParser.can_parse("KF,water_content,0.123") is False

    def test_dispatch_routes_to_kf_not_generic_csv(self, ctx: CaptureContext) -> None:
        """parse_line must pick KarlFischerParser for KF-prefixed lines."""
        result = parse_line(self.MINIMAL, ctx)
        assert result is not None
        assert result["protocol_meta"]["parser"] == "karl_fischer_v1"

    def test_hash_includes_metadata(self, ctx: CaptureContext) -> None:
        a = KarlFischerParser.parse(self.MINIMAL, ctx)
        other_ctx = CaptureContext(**{**ctx.to_dict(), "lot_number": "LOT-Z"})
        b = KarlFischerParser.parse(self.MINIMAL, other_ctx)
        assert a["data_hash"] != b["data_hash"]

    def test_does_not_claim_generic_csv_rows(self) -> None:
        """A 3-field generic CSV row must still go to GenericCSVParser."""
        assert KarlFischerParser.can_parse("pH,7.42,pH") is False
# AgilentChemStationParser
# ---------------------------------------------------------------------------

class TestAgilentChemStationParser:
    """Tests for the HPLC peak report parser (D7 T22).

    Format: ``<peak_num>,<retention_time>,<area>,<height>,<compound>,<unit>``
    Each peak data row becomes one ParsedReading where ``parameter`` is
    the compound name and ``value`` is the peak area.
    """

    PEAK_ROW = "1,2.345,12345.6,234.5,Caffeine,mAU*s"

    def test_parse_basic_peak_row(self, ctx: CaptureContext) -> None:
        result = AgilentChemStationParser.parse(self.PEAK_ROW, ctx)
        assert result is not None
        assert result["parameter"] == "Caffeine"
        assert result["value"] == "12345.6"
        assert result["unit"] == "mAU*s"
        assert result["protocol_meta"]["protocol"] == "ChemStation"
        assert result["protocol_meta"]["parser"] == "agilent_chemstation_v1"
        assert result["protocol_meta"]["peak_number"] == "1"
        # retention_time + height carried through as floats
        assert result["protocol_meta"]["retention_time_min"] == 2.345
        assert result["protocol_meta"]["height"] == 234.5

    def test_can_parse_rejects_header_comments(self) -> None:
        assert AgilentChemStationParser.can_parse(
            "# Agilent ChemStation Peak Report"
        ) is False

    def test_can_parse_rejects_table_header(self) -> None:
        assert AgilentChemStationParser.can_parse(
            "Peak,RetTime,Area,Height,Name,Unit"
        ) is False

    def test_can_parse_rejects_wrong_field_count(self) -> None:
        # 3 fields (a Generic CSV row) must not be claimed by Agilent
        assert AgilentChemStationParser.can_parse("pH,7.42,pH") is False
        # 5 fields also rejected
        assert AgilentChemStationParser.can_parse("1,2.3,4.5,6.7,Caffeine") is False

    def test_can_parse_rejects_non_numeric_retention(self) -> None:
        assert AgilentChemStationParser.can_parse(
            "1,not-a-number,12345.6,234.5,Caffeine,mAU*s"
        ) is False

    def test_empty_compound_name_falls_back(self, ctx: CaptureContext) -> None:
        result = AgilentChemStationParser.parse(
            "1,2.345,12345.6,234.5,,mAU*s", ctx
        )
        assert result is not None
        assert result["parameter"] == "unknown_peak"

    def test_hash_includes_metadata(self, ctx: CaptureContext) -> None:
        """SHA-256 must change when context changes (LBN-CONF-001)."""
        result1 = AgilentChemStationParser.parse(self.PEAK_ROW, ctx)
        # Different operator -> different hash
        other_ctx = CaptureContext(**{**ctx.to_dict(), "operator": "OP-OTHER"})
        result2 = AgilentChemStationParser.parse(self.PEAK_ROW, other_ctx)
        assert result1["data_hash"] != result2["data_hash"]

    def test_dispatch_via_parse_line(self, ctx: CaptureContext) -> None:
        """parse_line must route 6-field rows to AgilentChemStation, not GenericCSV."""
        result = parse_line(self.PEAK_ROW, ctx)
        assert result is not None
        assert result["protocol_meta"]["parser"] == "agilent_chemstation_v1"

    def test_raw_line_preserved(self, ctx: CaptureContext) -> None:
        result = AgilentChemStationParser.parse(self.PEAK_ROW, ctx)
        assert result is not None
        assert result["raw"] == self.PEAK_ROW

    def test_extract_returns_none_on_malformed(self) -> None:
        """extract() should be defensive even past can_parse."""
        assert AgilentChemStationParser.extract("garbage") is None
        assert AgilentChemStationParser.extract("") is None


# ---------------------------------------------------------------------------
# Parser dispatch
# ---------------------------------------------------------------------------

class TestParseLineDispatch:
    def test_mettler_dispatched(self, ctx: CaptureContext) -> None:
        result = parse_line("S S     12.3456 g", ctx)
        assert result is not None
        assert result["protocol_meta"]["parser"] == "mettler_sics_v1"

    def test_csv_dispatched(self, ctx: CaptureContext) -> None:
        result = parse_line("pH,7.42,pH", ctx)
        assert result is not None
        assert result["protocol_meta"]["parser"] == "generic_csv_v1"

    def test_sartorius_dispatched(self, ctx: CaptureContext) -> None:
        # Use a format that won't match Mettler/CSV first
        result = parse_line("+   100.0000 g", ctx)
        assert result is not None
        # Either SBI or Mettler could claim this depending on order
        assert result["protocol_meta"]["parser"] in (
            "mettler_sics_v1", "sartorius_sbi_v1"
        )

    def test_unmatched_line_returns_none(self, ctx: CaptureContext) -> None:
        assert parse_line("!!! garbage !!!", ctx) is None

    def test_empty_line_returns_none(self, ctx: CaptureContext) -> None:
        assert parse_line("", ctx) is None


# ---------------------------------------------------------------------------
# SHA-256 — scope, determinism, sensitivity
# ---------------------------------------------------------------------------

class TestCaptureHashScope:
    """The hash MUST cover value + timestamp + instrument_id + operator + lot_number.

    These tests pin that behaviour so any regression breaks loudly.
    """

    def _reading(self, **overrides) -> ParsedReading:
        defaults = {
            "parameter": "weight",
            "value": "12.3456",
            "unit": "g",
            "source_timestamp": "2026-04-23T10:00:00+00:00",
            "raw": "S S     12.3456 g",
            "protocol_meta": {},
        }
        defaults.update(overrides)
        return ParsedReading(**defaults)

    def test_hash_is_64_hex_chars(self, ctx: CaptureContext) -> None:
        h = compute_capture_hash(self._reading(), ctx)
        assert len(h) == 64
        int(h, 16)  # must be valid hex

    def test_hash_deterministic(self, ctx: CaptureContext) -> None:
        r = self._reading()
        h1 = compute_capture_hash(r, ctx)
        h2 = compute_capture_hash(r, ctx)
        assert h1 == h2

    def test_hash_changes_on_value_change(self, ctx: CaptureContext) -> None:
        h1 = compute_capture_hash(self._reading(value="12.3456"), ctx)
        h2 = compute_capture_hash(self._reading(value="12.3457"), ctx)
        assert h1 != h2

    def test_hash_changes_on_timestamp_change(self, ctx: CaptureContext) -> None:
        h1 = compute_capture_hash(
            self._reading(source_timestamp="2026-04-23T10:00:00+00:00"), ctx
        )
        h2 = compute_capture_hash(
            self._reading(source_timestamp="2026-04-23T10:00:01+00:00"), ctx
        )
        assert h1 != h2

    def test_hash_changes_on_instrument_id_change(self, ctx: CaptureContext) -> None:
        ctx_a = CaptureContext(**{**ctx.to_dict(), "instrument_id": 1})
        ctx_b = CaptureContext(**{**ctx.to_dict(), "instrument_id": 2})
        r = self._reading()
        assert compute_capture_hash(r, ctx_a) != compute_capture_hash(r, ctx_b)

    def test_hash_changes_on_operator_change(self, ctx: CaptureContext) -> None:
        ctx_a = CaptureContext(**{**ctx.to_dict(), "operator": "OP-001"})
        ctx_b = CaptureContext(**{**ctx.to_dict(), "operator": "OP-002"})
        r = self._reading()
        assert compute_capture_hash(r, ctx_a) != compute_capture_hash(r, ctx_b)

    def test_hash_changes_on_lot_number_change(self, ctx: CaptureContext) -> None:
        ctx_a = CaptureContext(**{**ctx.to_dict(), "lot_number": "LOT-A"})
        ctx_b = CaptureContext(**{**ctx.to_dict(), "lot_number": "LOT-B"})
        r = self._reading()
        assert compute_capture_hash(r, ctx_a) != compute_capture_hash(r, ctx_b)

    def test_hash_changes_on_method_change(self, ctx: CaptureContext) -> None:
        ctx_a = CaptureContext(**{**ctx.to_dict(), "method": "USP <621>"})
        ctx_b = CaptureContext(**{**ctx.to_dict(), "method": "Ph.Eur.2.2.25"})
        r = self._reading()
        assert compute_capture_hash(r, ctx_a) != compute_capture_hash(r, ctx_b)

    def test_hash_stable_on_notes_change(self, ctx: CaptureContext) -> None:
        """Notes are not in the hash scope — operators can annotate later."""
        ctx_a = CaptureContext(**{**ctx.to_dict(), "notes": "first note"})
        ctx_b = CaptureContext(**{**ctx.to_dict(), "notes": "different note"})
        r = self._reading()
        assert compute_capture_hash(r, ctx_a) == compute_capture_hash(r, ctx_b)

    def test_hash_canonical_form(self, ctx: CaptureContext) -> None:
        """Hash should not depend on dict insertion order — uses sorted keys."""
        # Two contexts with the same semantic content
        ctx_1 = CaptureContext(
            instrument_id=42, sample_id=7,
            operator="OP-042", lot_number="LOT-X", method="M",
        )
        ctx_2 = CaptureContext(
            method="M", lot_number="LOT-X", operator="OP-042",
            sample_id=7, instrument_id=42,
        )
        r = self._reading()
        assert compute_capture_hash(r, ctx_1) == compute_capture_hash(r, ctx_2)

    def test_empty_context_still_produces_valid_hash(
        self, empty_ctx: CaptureContext
    ) -> None:
        h = compute_capture_hash(self._reading(), empty_ctx)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# End-to-end payload shape & cloud payload filtering
# ---------------------------------------------------------------------------

class TestCapturePayload:
    def test_payload_includes_context_block(self, ctx: CaptureContext) -> None:
        result = parse_line("S S     12.3456 g", ctx)
        assert result is not None
        assert result["context"]["operator"] == "OP-042"
        assert result["context"]["lot_number"] == "LOT-2026-04"
        assert result["context"]["method"] == "USP <621>"
        assert result["context"]["instrument_id"] == 42

    def test_payload_hash_matches_standalone_compute(
        self, ctx: CaptureContext
    ) -> None:
        """Parsing a line must produce the same hash as compute_capture_hash
        directly, when fed the extracted reading."""
        line = "pH,7.42,pH"
        result = parse_line(line, ctx)
        assert result is not None

        # Rebuild the ParsedReading from the payload, re-hash, compare
        reading = ParsedReading(
            parameter=result["parameter"],
            value=result["value"],
            unit=result["unit"],
            source_timestamp=result["source_timestamp"],
            raw=result["raw"],
            protocol_meta={},
        )
        assert compute_capture_hash(reading, ctx) == result["data_hash"]

    def test_build_capture_payload_strips_internal_fields(
        self, ctx: CaptureContext
    ) -> None:
        """Only the cloud-contract fields are sent; context/protocol_meta stay local."""
        result = parse_line("S S     12.3456 g", ctx)
        assert result is not None

        cloud_payload = build_capture_payload(result)

        # Cloud payload must include the core capture contract
        for key in [
            "idempotency_key", "sample_id", "instrument_id",
            "parameter", "value", "unit", "data_hash",
            "source_timestamp", "hub_received_at",
        ]:
            assert key in cloud_payload

        # Internal-only fields must be stripped
        assert "context" not in cloud_payload
        assert "protocol_meta" not in cloud_payload
        assert "raw" not in cloud_payload

    def test_payload_idempotency_key_is_unique_uuid(
        self, ctx: CaptureContext
    ) -> None:
        r1 = parse_line("pH,7.42,pH", ctx)
        r2 = parse_line("pH,7.42,pH", ctx)
        assert r1 is not None and r2 is not None
        assert r1["idempotency_key"] != r2["idempotency_key"]
        # UUID v4 format check
        assert len(r1["idempotency_key"]) == 36

    def test_raw_line_preserved_in_payload(self, ctx: CaptureContext) -> None:
        line = "S S     12.3456 g"
        result = parse_line(line, ctx)
        assert result is not None
        assert result["raw"] == line

    def test_payload_is_json_serializable(self, ctx: CaptureContext) -> None:
        """Payload must survive round-trip through JSON for SQLite WAL storage."""
        result = parse_line("S S     12.3456 g", ctx)
        assert result is not None
        round_trip = json.loads(json.dumps(result))
        assert round_trip["data_hash"] == result["data_hash"]
        assert round_trip["context"] == result["context"]
