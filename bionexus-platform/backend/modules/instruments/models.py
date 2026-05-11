import hashlib

from django.db import models
from django.utils import timezone


class InstrumentConfig(models.Model):
    """Per-instrument configuration — the Configurable Layer (GAMP5 Cat 4).

    Each instrument has exactly one active config that defines:
    - Which parser protocol to use (binds to the parser registry)
    - Default measurement units
    - Which metadata fields operators MUST fill in (enforced at API level)
    - Threshold rules for automated log/alert/block actions

    Per LBN-CONF-002, changing config fields = GAMP5 Category 4 (configuration).
    Changing parser CODE = Category 5 (custom software) requiring full CSV.

    Threshold schema (JSON):
    {
        "weight_deviation": {"warn": 0.5, "block": 1.0, "unit": "%"},
        "ph_range": {"min": 6.8, "max": 7.6, "action": "alert"}
    }

    Required metadata fields schema (JSON list):
    ["operator", "lot_number", "method"]
    """

    PARSER_CHOICES = [
        ("mettler_sics_v1", "Mettler Toledo SICS"),
        ("sartorius_sbi_v1", "Sartorius SBI"),
        ("generic_csv_v1", "Generic CSV"),
        ("agilent_chemstation_v1", "Agilent ChemStation"),
        ("karl_fischer_v1", "Karl Fischer Titrator"),
        ("waters_empower_v1", "Waters Empower"),
        ("dissolution_ascii_v1", "Dissolution ASCII"),
    ]

    THRESHOLD_ACTION_CHOICES = [
        ("log", "Log — transparent recording, no user impact"),
        ("alert", "Alert — warning to operator, measurement continues"),
        ("block", "Block — reject measurement, require supervisor re-auth"),
    ]

    instrument = models.OneToOneField(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        related_name="config",
        help_text="The instrument this configuration applies to",
    )
    parser_type = models.CharField(
        max_length=50,
        choices=PARSER_CHOICES,
        help_text="Parser protocol from the registry (GAMP5 Cat 4 binding)",
    )
    units = models.CharField(
        max_length=50,
        default="",
        blank=True,
        help_text="Default measurement unit for this instrument (e.g., g, pH, AU, mg/L)",
    )
    required_metadata_fields = models.JSONField(
        default=list,
        blank=True,
        help_text='List of MeasurementContext fields that must be provided. '
                  'e.g., ["operator", "lot_number", "method"]',
    )
    thresholds = models.JSONField(
        default=dict,
        blank=True,
        help_text="Threshold rules per parameter. Keys: parameter names, "
                  "values: {warn, block, min, max, unit, action}",
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=255,
        blank=True,
        help_text="Who created this config (pseudonymized operator ID)",
    )

    class Meta:
        app_label = "instruments"
        verbose_name = "Instrument Configuration"
        verbose_name_plural = "Instrument Configurations"

    def __str__(self) -> str:
        return f"Config({self.parser_type}) for {self.instrument}"

    def get_required_fields(self) -> list[str]:
        """Return the list of required MeasurementContext field names."""
        if isinstance(self.required_metadata_fields, list):
            return self.required_metadata_fields
        return []

    def validate_context(self, context_data: dict) -> list[str]:
        """Check if context_data satisfies required_metadata_fields.

        Returns a list of missing field names (empty = valid).
        """
        required = self.get_required_fields()
        missing = []
        for field in required:
            value = context_data.get(field, "")
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing

    def evaluate_threshold(self, parameter: str, value: float) -> str:
        """Evaluate a measurement value against configured thresholds.

        Returns the action to take: 'log', 'alert', or 'block'.
        Falls back to 'log' if no threshold is configured for the parameter.
        """
        if not isinstance(self.thresholds, dict):
            return "log"

        rule = self.thresholds.get(parameter)
        if not rule or not isinstance(rule, dict):
            return "log"

        # Range-based threshold (min/max)
        if "min" in rule and value < rule["min"]:
            return rule.get("action", "alert")
        if "max" in rule and value > rule["max"]:
            return rule.get("action", "alert")

        # Deviation-based threshold (warn/block)
        if "block" in rule and abs(value) >= rule["block"]:
            return "block"
        if "warn" in rule and abs(value) >= rule["warn"]:
            return "alert"

        return "log"


class Instrument(models.Model):
    """A laboratory instrument connected via the BioNexus Box gateway.

    Tracks instrument identity, connection method, and operational status.
    Soft-delete preserves data for audit compliance.
    """

    CONNECTION_TYPES = [
        ("RS232", "RS232"),
        ("USB", "USB"),
        ("Ethernet", "Ethernet"),
        ("WiFi", "WiFi"),
    ]

    STATUS_CHOICES = [
        ("online", "Online"),
        ("offline", "Offline"),
        ("error", "Error"),
    ]

    name = models.CharField(max_length=255, help_text="Instrument display name")
    instrument_type = models.CharField(
        max_length=100, help_text="e.g., spectrophotometer, pH meter, HPLC"
    )
    serial_number = models.CharField(
        max_length=255, unique=True, help_text="Manufacturer serial number"
    )
    connection_type = models.CharField(
        max_length=20, choices=CONNECTION_TYPES, help_text="Physical connection method"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="offline"
    )

    # Soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "instruments"
        indexes = [
            models.Index(fields=["is_deleted", "id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
