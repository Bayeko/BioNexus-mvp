"""Tests for InstrumentConfig model and API.

Covers:
- Model creation, defaults, and JSON fields
- OneToOne relationship with Instrument
- Parser type choices validation
- Threshold evaluation logic (log/alert/block)
- Required metadata field validation
- API CRUD (happy path + errors)
- Instrument API includes nested config
"""

from django.test import TestCase
from rest_framework.test import APIClient

from modules.instruments.models import Instrument, InstrumentConfig


class InstrumentConfigModelTest(TestCase):
    """Unit tests for the InstrumentConfig model."""

    def setUp(self) -> None:
        self.instrument = Instrument.objects.create(
            name="Mettler XPE205",
            instrument_type="Balance",
            serial_number="MT-CFG-001",
            connection_type="RS232",
        )

    def test_create_config_full(self) -> None:
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
            units="g",
            required_metadata_fields=["operator", "lot_number", "method"],
            thresholds={
                "weight": {"warn": 0.5, "block": 1.0, "unit": "%"},
                "temperature": {"min": 20.0, "max": 25.0, "action": "alert"},
            },
            created_by="admin-001",
        )
        self.assertEqual(config.parser_type, "mettler_sics_v1")
        self.assertEqual(config.units, "g")
        self.assertEqual(len(config.required_metadata_fields), 3)
        self.assertIn("weight", config.thresholds)
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)

    def test_create_config_defaults(self) -> None:
        """JSON fields default to empty list/dict."""
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
        )
        self.assertEqual(config.required_metadata_fields, [])
        self.assertEqual(config.thresholds, {})
        self.assertEqual(config.units, "")

    def test_one_to_one_enforcement(self) -> None:
        """Only one config per instrument."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            InstrumentConfig.objects.create(
                instrument=self.instrument,
                parser_type="sartorius_sbi_v1",
            )

    def test_cascade_delete(self) -> None:
        """Deleting instrument cascades to its config."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
        )
        self.assertEqual(InstrumentConfig.objects.count(), 1)
        self.instrument.delete()
        self.assertEqual(InstrumentConfig.objects.count(), 0)

    def test_reverse_access_from_instrument(self) -> None:
        """Instrument.config returns the attached config."""
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
        )
        self.assertEqual(self.instrument.config, config)

    def test_str_representation(self) -> None:
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="mettler_sics_v1",
        )
        s = str(config)
        self.assertIn("mettler_sics_v1", s)
        self.assertIn("MT-CFG-001", s)


class InstrumentConfigValidationTest(TestCase):
    """Tests for InstrumentConfig business logic methods."""

    def setUp(self) -> None:
        self.instrument = Instrument.objects.create(
            name="pH Meter",
            instrument_type="pH Meter",
            serial_number="PH-VAL-001",
            connection_type="RS232",
        )
        self.config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
            units="pH",
            required_metadata_fields=["operator", "lot_number"],
            thresholds={
                "pH": {"min": 6.8, "max": 7.6, "action": "alert"},
                "weight_deviation": {"warn": 0.5, "block": 1.0, "unit": "%"},
            },
        )

    # --- validate_context tests ---

    def test_validate_context_all_present(self) -> None:
        missing = self.config.validate_context({
            "operator": "OP-001",
            "lot_number": "LOT-001",
        })
        self.assertEqual(missing, [])

    def test_validate_context_missing_required(self) -> None:
        missing = self.config.validate_context({
            "operator": "OP-001",
            # lot_number missing
        })
        self.assertEqual(missing, ["lot_number"])

    def test_validate_context_empty_string_counts_as_missing(self) -> None:
        missing = self.config.validate_context({
            "operator": "",
            "lot_number": "LOT-001",
        })
        self.assertEqual(missing, ["operator"])

    def test_validate_context_whitespace_only_counts_as_missing(self) -> None:
        missing = self.config.validate_context({
            "operator": "   ",
            "lot_number": "LOT-001",
        })
        self.assertEqual(missing, ["operator"])

    def test_validate_context_no_required_fields(self) -> None:
        """Config with empty required list accepts anything."""
        self.config.required_metadata_fields = []
        self.config.save()
        missing = self.config.validate_context({})
        self.assertEqual(missing, [])

    def test_get_required_fields(self) -> None:
        self.assertEqual(
            self.config.get_required_fields(), ["operator", "lot_number"]
        )

    # --- evaluate_threshold tests ---

    def test_threshold_in_range_returns_log(self) -> None:
        self.assertEqual(self.config.evaluate_threshold("pH", 7.2), "log")

    def test_threshold_below_min_returns_alert(self) -> None:
        self.assertEqual(self.config.evaluate_threshold("pH", 6.5), "alert")

    def test_threshold_above_max_returns_alert(self) -> None:
        self.assertEqual(self.config.evaluate_threshold("pH", 8.0), "alert")

    def test_threshold_warn_level(self) -> None:
        self.assertEqual(
            self.config.evaluate_threshold("weight_deviation", 0.7), "alert"
        )

    def test_threshold_block_level(self) -> None:
        self.assertEqual(
            self.config.evaluate_threshold("weight_deviation", 1.5), "block"
        )

    def test_threshold_below_warn_returns_log(self) -> None:
        self.assertEqual(
            self.config.evaluate_threshold("weight_deviation", 0.3), "log"
        )

    def test_threshold_unknown_parameter_returns_log(self) -> None:
        self.assertEqual(
            self.config.evaluate_threshold("conductivity", 100.0), "log"
        )

    def test_threshold_empty_config_returns_log(self) -> None:
        self.config.thresholds = {}
        self.config.save()
        self.assertEqual(self.config.evaluate_threshold("pH", 99.0), "log")


class InstrumentConfigAPITest(TestCase):
    """Integration tests for InstrumentConfig API endpoints."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.instrument = Instrument.objects.create(
            name="HPLC Agilent 1260",
            instrument_type="HPLC",
            serial_number="AG-API-001",
            connection_type="Ethernet",
        )

    def test_create_config_via_api(self) -> None:
        payload = {
            "instrument": self.instrument.pk,
            "parser_type": "agilent_chemstation_v1",
            "units": "AU",
            "required_metadata_fields": ["operator", "method"],
            "thresholds": {
                "absorbance": {"min": 0.0, "max": 3.0, "action": "alert"}
            },
            "created_by": "admin-001",
        }
        response = self.client.post(
            "/api/instrument-configs/", payload, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["parser_type"], "agilent_chemstation_v1")
        self.assertEqual(response.data["units"], "AU")
        self.assertEqual(response.data["required_metadata_fields"], ["operator", "method"])

    def test_list_configs(self) -> None:
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
        )
        response = self.client.get("/api/instrument-configs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_config_detail(self) -> None:
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="waters_empower_v1",
            units="mg/L",
        )
        response = self.client.get(f"/api/instrument-configs/{config.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["parser_type"], "waters_empower_v1")

    def test_update_config(self) -> None:
        config = InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
        )
        response = self.client.patch(
            f"/api/instrument-configs/{config.pk}/",
            {"units": "mL", "required_metadata_fields": ["operator"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["units"], "mL")

    def test_invalid_required_field_name_rejected(self) -> None:
        payload = {
            "instrument": self.instrument.pk,
            "parser_type": "generic_csv_v1",
            "required_metadata_fields": ["operator", "invalid_field_xyz"],
        }
        response = self.client.post(
            "/api/instrument-configs/", payload, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("required_metadata_fields", response.data)

    def test_instrument_includes_nested_config(self) -> None:
        """GET /api/instruments/{id}/ includes nested config."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="agilent_chemstation_v1",
            units="AU",
        )
        response = self.client.get(f"/api/instruments/{self.instrument.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("config", response.data)
        self.assertEqual(response.data["config"]["parser_type"], "agilent_chemstation_v1")

    def test_instrument_without_config_shows_null(self) -> None:
        """GET /api/instruments/{id}/ shows null config when not configured."""
        response = self.client.get(f"/api/instruments/{self.instrument.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["config"])

    def test_create_config_missing_parser_type_fails(self) -> None:
        response = self.client.post(
            "/api/instrument-configs/",
            {"instrument": self.instrument.pk, "units": "g"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_config_for_same_instrument_fails(self) -> None:
        """Cannot create two configs for the same instrument via API."""
        InstrumentConfig.objects.create(
            instrument=self.instrument,
            parser_type="generic_csv_v1",
        )
        response = self.client.post(
            "/api/instrument-configs/",
            {"instrument": self.instrument.pk, "parser_type": "mettler_sics_v1"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
