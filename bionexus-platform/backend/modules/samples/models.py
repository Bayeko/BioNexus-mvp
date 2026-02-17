from django.db import models
from django.utils import timezone


class Sample(models.Model):
    """Model representing a biological sample.

    Soft delete fields (is_deleted, deleted_at) ensure that data is never
    permanently removed -- deletion is just a logical flag. This preserves
    the audit trail for compliance purposes.
    """

    name = models.CharField(max_length=255)
    sample_type = models.CharField(max_length=100)
    received_at = models.DateTimeField()
    location = models.CharField(max_length=255)

    # -- Soft Delete (for audit compliance) ------------------------------------
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Logical deletion marker (data is never physically removed)",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when logically deleted (null if not deleted)",
    )

    class Meta:
        app_label = "samples"
        indexes = [
            models.Index(fields=["is_deleted", "id"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name

    def soft_delete(self) -> None:
        """Logically delete the sample (data preserved in DB for audit)."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
