import hashlib
import json
import uuid

from django.db import models


class MeasurementContext(models.Model):
    """Operational context captured at the time of a measurement.

    Records WHO performed the measurement, WHAT method/lot was involved, and
    any operator notes. This metadata layer is what differentiates BioNexus
    from generic LIMS: structured context, not just raw data.

    Per LBN-CONF-001, each InstrumentConfig can enforce which context fields
    are required via ``required_metadata_fields``. Validation happens at the
    serializer/service layer, not at the DB level, so partial contexts can
    still be stored (e.g., instrument-only readings without an operator).
    """

    measurement = models.OneToOneField(
        "measurements.Measurement",
        on_delete=models.CASCADE,
        related_name="context",
        help_text="The measurement this context belongs to",
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="measurement_contexts",
        help_text="Instrument that produced this reading (denormalized for query performance)",
    )
    operator = models.CharField(
        max_length=255,
        blank=True,
        help_text="Pseudonymized operator identifier (never PII)",
    )
    lot_number = models.CharField(
        max_length=255,
        blank=True,
        help_text="Lot/batch number being tested",
    )
    method = models.CharField(
        max_length=255,
        blank=True,
        help_text="Analytical method reference (e.g., USP <621>, Ph. Eur. 2.2.25)",
    )
    sample_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="External sample identifier from the QC workflow",
    )
    notes = models.TextField(
        blank=True,
        help_text="Free-text operator notes or observations",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this context record was created",
    )

    class Meta:
        app_label = "measurements"
        indexes = [
            models.Index(fields=["instrument", "timestamp"]),
            models.Index(fields=["lot_number"]),
            models.Index(fields=["operator"]),
        ]

    def __str__(self) -> str:
        parts = []
        if self.operator:
            parts.append(f"op={self.operator}")
        if self.lot_number:
            parts.append(f"lot={self.lot_number}")
        if self.method:
            parts.append(f"method={self.method}")
        return f"Context({', '.join(parts) or 'empty'}) for Measurement#{self.measurement_id}"


class Measurement(models.Model):
    """A single data point captured from a laboratory instrument.

    This is the core data capture model. Each measurement records a parameter
    reading (e.g., pH, temperature, absorbance) from an instrument for a sample.
    A SHA-256 data hash ensures data integrity per 21 CFR Part 11.
    """

    sample = models.ForeignKey(
        "samples.Sample",
        on_delete=models.PROTECT,
        related_name="measurements",
        help_text="Sample this measurement belongs to",
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="measurements",
        help_text="Instrument that produced this reading",
    )
    parameter = models.CharField(
        max_length=255, help_text="What was measured (e.g., pH, temperature, absorbance)"
    )
    value = models.DecimalField(
        max_digits=20, decimal_places=10, help_text="Measured value"
    )
    unit = models.CharField(
        max_length=50, help_text="Unit of measurement (e.g., pH, °C, AU, mg/L)"
    )
    measured_at = models.DateTimeField(
        help_text="When the measurement was taken (instrument timestamp)"
    )
    data_hash = models.CharField(
        max_length=64,
        editable=False,
        help_text="SHA-256 hash of measurement data for integrity verification",
    )
    idempotency_key = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="UUID from the hub WAL to prevent duplicate ingestion on retry",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "measurements"
        indexes = [
            models.Index(fields=["sample", "created_at"]),
            models.Index(fields=["instrument", "measured_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.parameter}={self.value}{self.unit} @ {self.measured_at}"

    def save(self, *args, **kwargs):
        # Compute SHA-256 data hash before every save
        self.data_hash = self._compute_hash()
        super().save(*args, **kwargs)

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of the measurement data for integrity proof."""
        payload = json.dumps(
            {
                "sample_id": self.sample_id,
                "instrument_id": self.instrument_id,
                "parameter": self.parameter,
                "value": str(self.value),
                "unit": self.unit,
                "measured_at": self.measured_at.isoformat() if self.measured_at else "",
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
