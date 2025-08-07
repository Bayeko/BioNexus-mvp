from rest_framework import viewsets

from .models import Protocol
from .serializers import ProtocolSerializer


class ProtocolViewSet(viewsets.ModelViewSet):
    """API endpoint for listing and managing protocols."""

    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
