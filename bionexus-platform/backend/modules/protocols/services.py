"""Business logic layer for the Protocols module.

Same architectural pattern as the Samples service -- views delegate here,
and this layer is the only one that may call the repository.
"""

from django.db.models import QuerySet

from .exceptions import ProtocolNotFoundError, ProtocolValidationError
from .models import Protocol
from .repositories import ProtocolRepository


class ProtocolService:
    """Orchestrates validation and persistence for Protocol entities."""

    def __init__(self, repository: ProtocolRepository | None = None):
        self._repo = repository or ProtocolRepository()

    # -- Read -----------------------------------------------------------------

    def list_protocols(self) -> QuerySet[Protocol]:
        return self._repo.get_all()

    def get_protocol(self, protocol_id: int) -> Protocol:
        protocol = self._repo.get_by_id(protocol_id)
        if protocol is None:
            raise ProtocolNotFoundError(protocol_id)
        return protocol

    # -- Write ----------------------------------------------------------------

    def create_protocol(self, data: dict) -> Protocol:
        self._validate_create(data)
        return self._repo.create(data)

    def update_protocol(self, protocol_id: int, data: dict) -> Protocol:
        protocol = self.get_protocol(protocol_id)
        self._validate_update(data)
        return self._repo.update(protocol, data)

    def delete_protocol(self, protocol_id: int) -> None:
        protocol = self.get_protocol(protocol_id)
        self._repo.delete(protocol)

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
