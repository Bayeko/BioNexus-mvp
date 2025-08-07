from rest_framework import serializers, viewsets

from .models import Protocol


class ProtocolSerializer(serializers.ModelSerializer):
    """Serializer for the Protocol model."""

    class Meta:
        model = Protocol
        fields = ["id", "title", "description", "steps"]


class ProtocolViewSet(viewsets.ModelViewSet):
    """API endpoint for listing and managing protocols."""

    queryset = Protocol.objects.all()
    serializer_class = ProtocolSerializer
