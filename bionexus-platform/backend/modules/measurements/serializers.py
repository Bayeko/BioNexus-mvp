from rest_framework import serializers

from .models import Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = [
            "id",
            "sample",
            "instrument",
            "parameter",
            "value",
            "unit",
            "measured_at",
            "data_hash",
            "created_at",
        ]
        read_only_fields = ["id", "data_hash", "created_at"]
