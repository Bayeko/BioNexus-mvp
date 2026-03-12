import hashlib

from django.db import models
from django.utils import timezone


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
