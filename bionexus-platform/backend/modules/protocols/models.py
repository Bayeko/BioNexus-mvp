from django.db import models
from django.utils import timezone


class Protocol(models.Model):
    """Represents a laboratory or analysis protocol.

    Soft delete fields ensure deletion is auditable and reversible.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    steps = models.TextField(blank=True)

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
        app_label = "protocols"
        indexes = [
            models.Index(fields=["is_deleted", "id"]),
        ]

    def __str__(self) -> str:
        return self.title

    def soft_delete(self) -> None:
        """Logically delete the protocol (data preserved in DB for audit)."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
