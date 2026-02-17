"""Data access layer for the Samples module.

All ORM queries for Sample are centralised here.  No other layer should
call ``Sample.objects`` directly -- always go through this repository so
that query logic stays in one place and can be optimised independently.
"""

from django.db.models import QuerySet

from .models import Sample


class SampleRepository:
    """Encapsulates all database operations for the Sample model."""

    # -- Read -----------------------------------------------------------------

    @staticmethod
    def get_all() -> QuerySet[Sample]:
        return Sample.objects.all()

    @staticmethod
    def get_by_id(sample_id: int) -> Sample | None:
        try:
            return Sample.objects.get(pk=sample_id)
        except Sample.DoesNotExist:
            return None

    # -- Write ----------------------------------------------------------------

    @staticmethod
    def create(data: dict) -> Sample:
        return Sample.objects.create(**data)

    @staticmethod
    def update(sample: Sample, data: dict) -> Sample:
        for field, value in data.items():
            setattr(sample, field, value)
        sample.save(update_fields=list(data.keys()))
        return sample

    @staticmethod
    def delete(sample: Sample) -> None:
        sample.delete()
