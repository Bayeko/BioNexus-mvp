from rest_framework import serializers

from .models import Protocol


class ProtocolSerializer(serializers.ModelSerializer):
    """Serializer for the Protocol model."""

    class Meta:
        model = Protocol
        fields = ["id", "title", "description", "steps"]
