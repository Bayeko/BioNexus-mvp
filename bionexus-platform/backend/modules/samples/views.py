"""HTTP layer for the Samples module.

Views are intentionally thin.  They:
  1. Deserialise / validate the incoming HTTP request via the serializer.
  2. Delegate to :class:`SampleService` for business logic.
  3. Serialise and return the response.

No model is instantiated or saved here -- that responsibility belongs
exclusively to the service and repository layers.
"""

from rest_framework import status, viewsets
from rest_framework.response import Response

from .exceptions import SampleNotFoundError, SampleValidationError
from .serializers import SampleSerializer
from .services import SampleService


class SampleViewSet(viewsets.ViewSet):
    """CRUD endpoints for Sample, delegating all logic to SampleService."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service = SampleService()

    # GET /api/samples/
    def list(self, request):
        samples = self._service.list_samples()
        serializer = SampleSerializer(samples, many=True)
        return Response(serializer.data)

    # POST /api/samples/
    def create(self, request):
        serializer = SampleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sample = self._service.create_sample(serializer.validated_data)
        except SampleValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            SampleSerializer(sample).data,
            status=status.HTTP_201_CREATED,
        )

    # GET /api/samples/{id}/
    def retrieve(self, request, pk=None):
        try:
            sample = self._service.get_sample(int(pk))
        except SampleNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(SampleSerializer(sample).data)

    # PATCH /api/samples/{id}/
    def partial_update(self, request, pk=None):
        try:
            sample = self._service.get_sample(int(pk))
        except SampleNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SampleSerializer(sample, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = self._service.update_sample(int(pk), serializer.validated_data)
        except SampleValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(SampleSerializer(updated).data)

    # PUT /api/samples/{id}/
    def update(self, request, pk=None):
        try:
            sample = self._service.get_sample(int(pk))
        except SampleNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SampleSerializer(sample, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = self._service.update_sample(int(pk), serializer.validated_data)
        except SampleValidationError as exc:
            return Response(exc.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(SampleSerializer(updated).data)

    # DELETE /api/samples/{id}/
    def destroy(self, request, pk=None):
        try:
            self._service.delete_sample(int(pk))
        except SampleNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
