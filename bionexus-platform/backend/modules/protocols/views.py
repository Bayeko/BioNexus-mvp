"""HTTP layer for the Protocols module.

Same thin-view pattern as Samples.  All business logic lives in
:class:`ProtocolService`.
"""

from rest_framework import status, viewsets
from rest_framework.response import Response

from .exceptions import ProtocolNotFoundError, ProtocolValidationError
from .serializers import ProtocolSerializer
from .services import ProtocolService


class ProtocolViewSet(viewsets.ViewSet):
    """CRUD endpoints for Protocol, delegating all logic to ProtocolService."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = ProtocolService()

    # GET /api/protocols/
    def list(self, request):
        protocols = self._service.list_protocols()
        serializer = ProtocolSerializer(protocols, many=True)
        return Response(serializer.data)

    # POST /api/protocols/
    def create(self, request):
        serializer = ProtocolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            protocol = self._service.create_protocol(serializer.validated_data)
        except ProtocolValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ProtocolSerializer(protocol).data,
            status=status.HTTP_201_CREATED,
        )

    # GET /api/protocols/{id}/
    def retrieve(self, request, pk=None):
        try:
            protocol = self._service.get_protocol(int(pk))
        except ProtocolNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(ProtocolSerializer(protocol).data)

    # PATCH /api/protocols/{id}/
    def partial_update(self, request, pk=None):
        try:
            protocol = self._service.get_protocol(int(pk))
        except ProtocolNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ProtocolSerializer(protocol, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = self._service.update_protocol(
                int(pk), serializer.validated_data
            )
        except ProtocolValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(ProtocolSerializer(updated).data)

    # PUT /api/protocols/{id}/
    def update(self, request, pk=None):
        try:
            protocol = self._service.get_protocol(int(pk))
        except ProtocolNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ProtocolSerializer(protocol, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = self._service.update_protocol(
                int(pk), serializer.validated_data
            )
        except ProtocolValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(ProtocolSerializer(updated).data)

    # DELETE /api/protocols/{id}/
    def destroy(self, request, pk=None):
        try:
            self._service.delete_protocol(int(pk))
        except ProtocolNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
