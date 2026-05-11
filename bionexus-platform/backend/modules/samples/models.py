from django.db import models
from django.utils import timezone


class Sample(models.Model):
    """A tracked sample processed by a laboratory instrument.

    Tracks sample identity, which instrument processed it, batch info,
    and processing status. Soft-delete preserves data for audit compliance.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    sample_id = models.CharField(
        max_length=100, unique=True, help_text="Business identifier (e.g., SMP-2024-001)"
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="samples",
        help_text="Instrument that processes this sample",
    )
    batch_number = models.CharField(max_length=100, help_text="Batch or lot number")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_by = models.CharField(
        max_length=255, help_text="Username or identifier of the creator"
    )

    # Soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "samples"
        indexes = [
            models.Index(fields=["is_deleted", "id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["batch_number"]),
        ]

    def __str__(self) -> str:
        return self.sample_id

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
