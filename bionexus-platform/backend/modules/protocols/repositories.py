"""Data access layer for the Protocols module.

All ORM queries for Protocol are centralised here.  No other layer should
call ``Protocol.objects`` directly -- always go through this repository.
"""

from django.db.models import QuerySet

from .models import Protocol


class ProtocolRepository:
    """Encapsulates all database operations for the Protocol model."""

    # -- Read -----------------------------------------------------------------

    @staticmethod
    def get_all() -> QuerySet[Protocol]:
        return Protocol.objects.all()

    @staticmethod
    def get_by_id(protocol_id: int) -> Protocol | None:
        try:
            return Protocol.objects.get(pk=protocol_id)
        except Protocol.DoesNotExist:
            return None

    # -- Write ----------------------------------------------------------------

    @staticmethod
    def create(data: dict) -> Protocol:
        return Protocol.objects.create(**data)

    @staticmethod
    def update(protocol: Protocol, data: dict) -> Protocol:
        for field, value in data.items():
            setattr(protocol, field, value)
        protocol.save(update_fields=list(data.keys()))
        return protocol

    @staticmethod
    def delete(protocol: Protocol) -> None:
        protocol.delete()
