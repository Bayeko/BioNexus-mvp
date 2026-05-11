"""HTTP layer for the Samples module.

Uses DRF ModelViewSet for standard CRUD. Audit trail is handled
automatically via Django signals (core.signals).
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Sample
from .serializers import SampleSerializer


class SampleViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for samples with filtering support.

    GET    /api/samples/                     — List samples (filterable)
    POST   /api/samples/                     — Create a sample
    GET    /api/samples/{id}/                — Get sample details
    PUT    /api/samples/{id}/                — Full update
    PATCH  /api/samples/{id}/                — Partial update (e.g., status)
    DELETE /api/samples/{id}/                — Soft-delete

    Filters:
      ?instrument={id}       — Filter by instrument
      ?status={status}       — Filter by status
      ?batch_number={batch}  — Filter by batch
      ?created_at__date={YYYY-MM-DD}  — Filter by date
    """

    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "instrument": ["exact"],
        "status": ["exact"],
        "batch_number": ["exact", "icontains"],
        "created_at": ["date", "gte", "lte"],
    }

    def get_queryset(self):
        return Sample.objects.filter(is_deleted=False).order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        sample = self.get_object()
        sample.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
