"""Write-Ahead Log model for offline persistence.

Every measurement from the BioNexus Box hub is written here FIRST,
before any network attempt. This guarantees zero data loss regardless
of network state.
"""

import uuid

from django.db import models


class PendingMeasurement(models.Model):
    """Local WAL record for a measurement awaiting server sync.

    Mirrors Measurement fields as raw values (no FK constraints) so the hub
    can write even when the server DB is unreachable. The idempotency_key
    prevents duplicates across retries.
    """

    SYNC_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("syncing", "Syncing"),
        ("synced", "Synced"),
        ("failed", "Failed"),
    ]

    # --- Deduplication ---
    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Hub-generated UUID to prevent duplicate ingestion on retry",
    )

    # --- Raw measurement data (no FK constraints for offline writes) ---
    sample_id = models.IntegerField(
        help_text="Raw FK to samples.Sample (no constraint for offline)",
    )
    instrument_id = models.IntegerField(
        help_text="Raw FK to instruments.Instrument (no constraint for offline)",
    )
    parameter = models.CharField(
        max_length=255,
        help_text="What was measured (e.g., pH, temperature, absorbance)",
    )
    value = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Measured value",
    )
    unit = models.CharField(
        max_length=50,
        help_text="Unit of measurement",
    )
    data_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 from instrument. SACRED: never recomputed server-side",
    )

    # --- Deterministic Timestamps (3-layer) ---
    source_timestamp = models.DateTimeField(
        help_text="Instrument emission timestamp. SACRED: never overwritten",
    )
    hub_received_at = models.DateTimeField(
        help_text="Hub local RTC time when data arrived at the WAL",
    )
    server_received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Server UTC time when data was ingested (set at ingest)",
    )

    # --- Clock Drift Detection ---
    clock_drift_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Delta (server_received_at - hub_received_at) in milliseconds",
    )
    drift_flagged = models.BooleanField(
        default=False,
        help_text="True if |clock_drift_ms| exceeds configured threshold",
    )

    # --- Sync State ---
    sync_status = models.CharField(
        max_length=10,
        choices=SYNC_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of failed sync attempts",
    )
    last_error = models.TextField(
        blank=True,
        help_text="Last sync error message",
    )
    synced_measurement_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Server-side Measurement PK after successful ACK",
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "persistence"
        indexes = [
            models.Index(fields=["sync_status", "created_at"]),
            models.Index(fields=["drift_flagged"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return (
            f"Pending {self.parameter}={self.value}{self.unit} "
            f"[{self.sync_status}] ({self.idempotency_key})"
        )

    def to_measurement_payload(self) -> dict:
        """Return dict suitable for creating a server-side Measurement."""
        return {
            "idempotency_key": str(self.idempotency_key),
            "sample_id": self.sample_id,
            "instrument_id": self.instrument_id,
            "parameter": self.parameter,
            "value": str(self.value),
            "unit": self.unit,
            "data_hash": self.data_hash,
            "source_timestamp": self.source_timestamp.isoformat(),
            "hub_received_at": self.hub_received_at.isoformat(),
        }
