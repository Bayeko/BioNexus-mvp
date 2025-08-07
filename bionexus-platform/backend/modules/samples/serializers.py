from rest_framework import serializers

from .models import Sample


class SampleSerializer(serializers.ModelSerializer):
    """Serializer for Sample model."""

    class Meta:
        model = Sample
        fields = ["id", "name", "sample_type", "received_at", "location"]
