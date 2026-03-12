import hashlib
import json
import uuid

from django.db import models


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
