"""Business logic layer for the Protocols module.

Same architectural pattern as the Samples service -- views delegate here,
and this layer is the only one that may call the repository.

Every mutation is recorded in an immutable audit trail.
"""

from django.db.models import QuerySet

from core.audit import AuditTrail

from .exceptions import ProtocolNotFoundError, ProtocolValidationError
from .models import Protocol
from .repositories import ProtocolRepository


class ProtocolService:
    """Orchestrates validation and persistence for Protocol entities."""

    def __init__(self, repository: ProtocolRepository | None = None):
        self._repo = repository or ProtocolRepository()

    # -- Read -----------------------------------------------------------------

    def list_protocols(self) -> QuerySet[Protocol]:
        # Exclude soft-deleted protocols from normal queries
        return self._repo.get_all().filter(is_deleted=False)

    def get_protocol(self, protocol_id: int) -> Protocol:
        protocol = self._repo.get_by_id(protocol_id)
        if protocol is None or protocol.is_deleted:
            raise ProtocolNotFoundError(protocol_id)
        return protocol

    # -- Write ----------------------------------------------------------------

    def create_protocol(self, data: dict) -> Protocol:
        self._validate_create(data)
        protocol = self._repo.create(data)

        # Record audit trail (serialize datetime objects if any)
        changes = {}
        for k, v in data.items():
            serialized_v = v.isoformat() if hasattr(v, "isoformat") else v
            changes[k] = {"before": None, "after": serialized_v}

        AuditTrail.record(
            entity_type="Protocol",
            entity_id=protocol.id,
            operation="CREATE",
            changes=changes,
            snapshot_before={},
            snapshot_after=self._model_to_dict(protocol),
        )

        return protocol

    def update_protocol(self, protocol_id: int, data: dict) -> Protocol:
        protocol = self.get_protocol(protocol_id)
        self._validate_update(data)

        # Capture state before mutation
        snapshot_before = self._model_to_dict(protocol)

        # Apply update
        updated = self._repo.update(protocol, data)

        # Record audit trail with before/after comparison
        changes = {}
        for field, value in data.items():
            before = snapshot_before.get(field)
            if before != value:
                changes[field] = {"before": before, "after": value}

        if changes:  # Only record if something actually changed
            AuditTrail.record(
                entity_type="Protocol",
                entity_id=protocol_id,
                operation="UPDATE",
                changes=changes,
                snapshot_before=snapshot_before,
                snapshot_after=self._model_to_dict(updated),
            )

        return updated

    def delete_protocol(self, protocol_id: int) -> None:
        protocol = self.get_protocol(protocol_id)

        # Capture state before deletion
        snapshot_before = self._model_to_dict(protocol)

        # Soft delete (logical deletion, no physical removal)
        protocol.soft_delete()

        # Record audit trail
        AuditTrail.record(
            entity_type="Protocol",
            entity_id=protocol_id,
            operation="DELETE",
            changes={"is_deleted": {"before": False, "after": True}},
            snapshot_before=snapshot_before,
            snapshot_after=self._model_to_dict(protocol),
        )

    # -- Helpers ---------------------------------------------------------------

    @staticmethod
    def _model_to_dict(protocol: Protocol) -> dict:
        """Convert a Protocol instance to a JSON-serializable dict.

        All datetime objects are converted to ISO strings for JSON compatibility.
        """

        def serialize_dt(dt):
            return dt.isoformat() if dt else None

        return {
            "id": protocol.id,
            "title": protocol.title,
            "description": protocol.description,
            "steps": protocol.steps,
            "is_deleted": protocol.is_deleted,
            "deleted_at": serialize_dt(protocol.deleted_at),
        }

    # -- Validation -----------------------------------------------------------

    @staticmethod
    def _validate_create(data: dict) -> None:
        errors: dict[str, str] = {}

        if not data.get("title", "").strip():
            errors["title"] = "Protocol title is required."

        if errors:
            raise ProtocolValidationError(errors)

    @staticmethod
    def _validate_update(data: dict) -> None:
        errors: dict[str, str] = {}

        title = data.get("title")
        if title is not None and not title.strip():
            errors["title"] = "Protocol title cannot be blank."

        if errors:
            raise ProtocolValidationError(errors)
