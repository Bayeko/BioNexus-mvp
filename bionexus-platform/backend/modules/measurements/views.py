from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import Measurement, MeasurementContext
from .serializers import MeasurementSerializer, MeasurementContextSerializer


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
        return Measurement.objects.select_related("context").all().order_by("-created_at")


class MeasurementContextViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for measurement context metadata.

    GET    /api/measurement-contexts/           — List contexts (filterable)
    POST   /api/measurement-contexts/           — Attach context to a measurement
    GET    /api/measurement-contexts/{id}/      — Get context details

    Filters:
      ?measurement={id}     — Filter by measurement
      ?instrument={id}      — Filter by instrument
      ?operator={name}      — Filter by operator
      ?lot_number={lot}     — Filter by lot number
    """

    serializer_class = MeasurementContextSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["measurement", "instrument", "operator", "lot_number"]

    def get_queryset(self):
        return MeasurementContext.objects.all().order_by("-timestamp")
