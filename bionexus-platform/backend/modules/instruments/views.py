from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import Instrument, InstrumentConfig
from .serializers import InstrumentSerializer, InstrumentConfigSerializer


class InstrumentViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for laboratory instruments.

    GET    /api/instruments/            — List all instruments
    POST   /api/instruments/            — Register a new instrument
    GET    /api/instruments/{id}/       — Get instrument details
    PUT    /api/instruments/{id}/       — Full update
    PATCH  /api/instruments/{id}/       — Partial update (e.g., status change)
    DELETE /api/instruments/{id}/       — Soft-delete
    GET    /api/instruments/{id}/config/ — Get the instrument's capture config
                                          (parser, units, required metadata fields,
                                          thresholds) — used by the frontend to
                                          drive the dynamic capture form.
    """

    serializer_class = InstrumentSerializer

    def get_queryset(self):
        return Instrument.objects.select_related("config").filter(
            is_deleted=False
        ).order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        instrument = self.get_object()
        instrument.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="config")
    def config(self, request, pk=None):
        """Return the capture config for this instrument.

        If no config is attached, return an empty-but-valid shape so the
        frontend can still render the form with no required fields.
        """
        instrument = self.get_object()
        config_obj = getattr(instrument, "config", None)

        if config_obj is None:
            return Response({
                "instrument": instrument.pk,
                "parser_type": "",
                "units": "",
                "required_metadata_fields": [],
                "thresholds": {},
                "configured": False,
            })

        data = InstrumentConfigSerializer(config_obj).data
        data["configured"] = True
        return Response(data)


class InstrumentConfigViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for instrument configuration (GAMP5 Cat 4).

    GET    /api/instrument-configs/          — List all configs
    POST   /api/instrument-configs/          — Create config for an instrument
    GET    /api/instrument-configs/{id}/     — Get config details
    PUT    /api/instrument-configs/{id}/     — Full update
    PATCH  /api/instrument-configs/{id}/     — Partial update
    """

    serializer_class = InstrumentConfigSerializer

    def get_queryset(self):
        return InstrumentConfig.objects.select_related("instrument").all().order_by(
            "-created_at"
        )
