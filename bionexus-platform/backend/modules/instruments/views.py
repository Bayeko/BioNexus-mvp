from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

from .models import Instrument
from .serializers import InstrumentSerializer


class InstrumentViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for laboratory instruments.

    GET    /api/instruments/          — List all instruments
    POST   /api/instruments/          — Register a new instrument
    GET    /api/instruments/{id}/     — Get instrument details
    PUT    /api/instruments/{id}/     — Full update
    PATCH  /api/instruments/{id}/     — Partial update (e.g., status change)
    DELETE /api/instruments/{id}/     — Soft-delete
    """

    serializer_class = InstrumentSerializer

    def get_queryset(self):
        return Instrument.objects.filter(is_deleted=False).order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        instrument = self.get_object()
        instrument.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
