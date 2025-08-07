from django.db import models


class Sample(models.Model):
    """Model representing a biological sample."""

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    received_at = models.DateTimeField()
    location = models.CharField(max_length=255)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name
