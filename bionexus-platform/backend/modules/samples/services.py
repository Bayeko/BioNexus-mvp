"""Business logic layer for the Samples module.

This service is the **single entry-point** for every operation that
touches Sample data.  Views must never instantiate or save a model
directly -- they call methods here instead.

GxP rationale:
  - Centralised validation ensures every write path enforces the same
    business rules.
  - A future audit-trail decorator can be applied at this layer
    without modifying views or repositories.
"""

from django.db.models import QuerySet
from django.utils import timezone

from .exceptions import SampleNotFoundError, SampleValidationError
from .models import Sample
from .repositories import SampleRepository

# Types accepted as sample_type -- extend as the lab's catalogue grows.
ALLOWED_SAMPLE_TYPES = {"blood", "plasma", "serum", "urine", "tissue", "dna", "rna"}


class SampleService:
    """Orchestrates validation and persistence for Sample entities."""

    def __init__(self, repository: SampleRepository | None = None):
        self._repo = repository or SampleRepository()

    # -- Read -----------------------------------------------------------------

    def list_samples(self) -> QuerySet[Sample]:
        return self._repo.get_all()

    def get_sample(self, sample_id: int) -> Sample:
        sample = self._repo.get_by_id(sample_id)
        if sample is None:
            raise SampleNotFoundError(sample_id)
        return sample

    # -- Write ----------------------------------------------------------------

    def create_sample(self, data: dict) -> Sample:
        self._validate_create(data)
        return self._repo.create(data)

    def update_sample(self, sample_id: int, data: dict) -> Sample:
        sample = self.get_sample(sample_id)
        self._validate_update(data)
        return self._repo.update(sample, data)

    def delete_sample(self, sample_id: int) -> None:
        sample = self.get_sample(sample_id)
        self._repo.delete(sample)

    # -- Validation -----------------------------------------------------------

    @staticmethod
    def _validate_create(data: dict) -> None:
        """Enforce business rules when creating a new sample."""
        errors: dict[str, str] = {}

        if not data.get("name", "").strip():
            errors["name"] = "Sample name is required."

        sample_type = data.get("sample_type", "")
        if sample_type and sample_type.lower() not in ALLOWED_SAMPLE_TYPES:
            errors["sample_type"] = (
                f"Invalid sample type '{sample_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_SAMPLE_TYPES))}."
            )

        received_at = data.get("received_at")
        if received_at and hasattr(received_at, "tzinfo") and received_at > timezone.now():
            errors["received_at"] = "received_at cannot be in the future."

        if errors:
            raise SampleValidationError(errors)

    @staticmethod
    def _validate_update(data: dict) -> None:
        """Enforce business rules when updating an existing sample."""
        errors: dict[str, str] = {}

        sample_type = data.get("sample_type")
        if sample_type and sample_type.lower() not in ALLOWED_SAMPLE_TYPES:
            errors["sample_type"] = (
                f"Invalid sample type '{sample_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_SAMPLE_TYPES))}."
            )

        received_at = data.get("received_at")
        if received_at and hasattr(received_at, "tzinfo") and received_at > timezone.now():
            errors["received_at"] = "received_at cannot be in the future."

        if errors:
            raise SampleValidationError(errors)
