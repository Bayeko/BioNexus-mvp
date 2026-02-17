"""Business logic layer for the Samples module.

This service is the **single entry-point** for every operation that
touches Sample data.  Views must never instantiate or save a model
directly -- they call methods here instead.

GxP rationale:
  - Centralised validation ensures every write path enforces the same
    business rules.
  - Every mutation is recorded in an immutable, tamper-proof audit trail.
  - Soft deletion (logical flag) preserves data for forensics.
"""

from django.db.models import QuerySet
from django.utils import timezone

from core.audit import AuditTrail

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
        # Exclude soft-deleted samples from normal queries
        return self._repo.get_all().filter(is_deleted=False)

    def get_sample(self, sample_id: int) -> Sample:
        sample = self._repo.get_by_id(sample_id)
        if sample is None or sample.is_deleted:
            raise SampleNotFoundError(sample_id)
        return sample

    # -- Write ----------------------------------------------------------------

    def create_sample(self, data: dict) -> Sample:
        self._validate_create(data)
        sample = self._repo.create(data)

        # Record audit trail (serialize datetime objects)
        changes = {}
        for k, v in data.items():
            serialized_v = v.isoformat() if hasattr(v, "isoformat") else v
            changes[k] = {"before": None, "after": serialized_v}

        AuditTrail.record(
            entity_type="Sample",
            entity_id=sample.id,
            operation="CREATE",
            changes=changes,
            snapshot_before={},
            snapshot_after=self._model_to_dict(sample),
        )

        return sample

    def update_sample(self, sample_id: int, data: dict) -> Sample:
        sample = self.get_sample(sample_id)
        self._validate_update(data)

        # Capture state before mutation
        snapshot_before = self._model_to_dict(sample)

        # Apply update
        updated = self._repo.update(sample, data)

        # Record audit trail with before/after comparison
        changes = {}
        for field, value in data.items():
            before = snapshot_before.get(field)
            if before != value:
                changes[field] = {"before": before, "after": value}

        if changes:  # Only record if something actually changed
            AuditTrail.record(
                entity_type="Sample",
                entity_id=sample_id,
                operation="UPDATE",
                changes=changes,
                snapshot_before=snapshot_before,
                snapshot_after=self._model_to_dict(updated),
            )

        return updated

    def delete_sample(self, sample_id: int) -> None:
        sample = self.get_sample(sample_id)

        # Capture state before deletion
        snapshot_before = self._model_to_dict(sample)

        # Soft delete (logical deletion, no physical removal)
        sample.soft_delete()

        # Record audit trail
        AuditTrail.record(
            entity_type="Sample",
            entity_id=sample_id,
            operation="DELETE",
            changes={"is_deleted": {"before": False, "after": True}},
            snapshot_before=snapshot_before,
            snapshot_after=self._model_to_dict(sample),
        )

    # -- Helpers ---------------------------------------------------------------

    @staticmethod
    def _model_to_dict(sample: Sample) -> dict:
        """Convert a Sample instance to a JSON-serializable dict.

        All datetime objects are converted to ISO strings for JSON compatibility.
        """

        def serialize_dt(dt):
            return dt.isoformat() if dt else None

        return {
            "id": sample.id,
            "name": sample.name,
            "sample_type": sample.sample_type,
            "received_at": serialize_dt(sample.received_at),
            "location": sample.location,
            "is_deleted": sample.is_deleted,
            "deleted_at": serialize_dt(sample.deleted_at),
        }

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
