from django.db import models


class Protocol(models.Model):
    """Represents a laboratory or analysis protocol."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    steps = models.TextField(blank=True)

    class Meta:
        app_label = "protocols"

    def __str__(self) -> str:
        return self.title
