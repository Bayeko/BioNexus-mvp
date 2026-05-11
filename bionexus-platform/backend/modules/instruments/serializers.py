from rest_framework import serializers

from .models import Instrument, InstrumentConfig


class InstrumentConfigSerializer(serializers.ModelSerializer):
    """Serializer for per-instrument configuration (GAMP5 Cat 4 layer)."""

    class Meta:
        model = InstrumentConfig
        fields = [
            "id",
            "instrument",
            "parser_type",
            "units",
            "required_metadata_fields",
            "thresholds",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_required_metadata_fields(self, value: list) -> list:
        """Ensure required_metadata_fields only contains valid field names."""
        valid_fields = {"operator", "lot_number", "method", "sample_id", "notes"}
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of field names.")
        invalid = set(value) - valid_fields
        if invalid:
            raise serializers.ValidationError(
                f"Invalid field names: {', '.join(sorted(invalid))}. "
                f"Valid options: {', '.join(sorted(valid_fields))}"
            )
        return value


class InstrumentSerializer(serializers.ModelSerializer):
    config = InstrumentConfigSerializer(read_only=True)

    class Meta:
        model = Instrument
        fields = [
            "id",
            "name",
            "instrument_type",
            "serial_number",
            "connection_type",
            "status",
            "created_at",
            "updated_at",
            "config",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
