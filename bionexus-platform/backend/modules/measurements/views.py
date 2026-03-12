from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import Measurement
from .serializers import MeasurementSerializer


class MeasurementViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for measurement data capture.

    GET    /api/measurements/           — List measurements (filterable)
    POST   /api/measurements/           — Record a measurement
    GET    /api/measurements/{id}/      — Get measurement details

    Filters:
      ?sample={id}          — Filter by sample
      ?instrument={id}      — Filter by instrument
      ?parameter={name}     — Filter by parameter name
    """

    serializer_class = MeasurementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sample", "instrument", "parameter"]

    def get_queryset(self):
        return Measurement.objects.all().order_by("-created_at")
