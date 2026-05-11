from django.db import transaction
from rest_framework import serializers

from .models import Measurement, MeasurementContext


class MeasurementContextSerializer(serializers.ModelSerializer):
    """Serializer for measurement operational context.

    Validates required_metadata_fields against the instrument's
    InstrumentConfig when the instrument has one configured.
    """

    class Meta:
        model = MeasurementContext
        fields = [
            "id",
            "measurement",
            "instrument",
            "operator",
            "lot_number",
            "method",
            "sample_id",
            "notes",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]

    def validate(self, attrs: dict) -> dict:
        """Enforce required_metadata_fields from InstrumentConfig if present."""
        instrument = attrs.get("instrument")
        if instrument and hasattr(instrument, "config"):
            config = instrument.config
            context_data = {
                "operator": attrs.get("operator", ""),
                "lot_number": attrs.get("lot_number", ""),
                "method": attrs.get("method", ""),
                "sample_id": attrs.get("sample_id", ""),
                "notes": attrs.get("notes", ""),
            }
            missing = config.validate_context(context_data)
            if missing:
                raise serializers.ValidationError(
                    {field: f"This field is required by instrument config." for field in missing}
                )
        return attrs


class NestedContextInputSerializer(serializers.Serializer):
    """Inline context payload for composite POST /api/measurements/.

    Does NOT require a `measurement` FK (it's filled in by the parent
    serializer after the measurement is created). The `instrument` can
    be omitted — it defaults to the parent measurement's instrument.
    """

    operator = serializers.CharField(required=False, allow_blank=True, default="")
    lot_number = serializers.CharField(required=False, allow_blank=True, default="")
    method = serializers.CharField(required=False, allow_blank=True, default="")
    sample_id = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MeasurementSerializer(serializers.ModelSerializer):
    """Measurement serializer with optional nested context.

    On POST, accept either:
      - Flat payload (legacy): {sample, instrument, parameter, value, unit, measured_at}
      - Composite payload: same + {"context": {operator, lot_number, method, ...}}

    The composite form atomically creates both Measurement and
    MeasurementContext in a single transaction, enforcing
    InstrumentConfig.required_metadata_fields at the API boundary.
    """

    # Read-only nested representation for GET
    context = MeasurementContextSerializer(read_only=True)
    # Write-only nested input for POST
    context_input = NestedContextInputSerializer(
        write_only=True, required=False, source="_context_input"
    )

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
            "idempotency_key",
            "created_at",
            "context",
            "context_input",
        ]
        read_only_fields = ["id", "data_hash", "created_at"]

    def to_internal_value(self, data):
        """Accept both ``context`` and ``context_input`` as the write key.

        Frontend typically sends ``context: {...}`` in the POST body. We
        remap that to the internal ``context_input`` field so DRF's nested
        validation kicks in without colliding with the read-only ``context``
        representation.
        """
        if isinstance(data, dict) and "context" in data and "context_input" not in data:
            # Only remap if context looks like nested data, not a read-only artifact
            ctx_val = data.get("context")
            if isinstance(ctx_val, dict):
                data = {**data, "context_input": ctx_val}
                data.pop("context", None)
        return super().to_internal_value(data)

    def validate(self, attrs: dict) -> dict:
        """Enforce InstrumentConfig.required_metadata_fields at composite create.

        If the instrument has a config with required fields, the context
        payload must cover them. Runs even if ``context_input`` is absent
        (treats absent context as "all fields missing").
        """
        instrument = attrs.get("instrument")
        context_data = attrs.get("_context_input")

        if instrument and hasattr(instrument, "config"):
            config = instrument.config
            to_check = context_data or {}
            missing = config.validate_context(to_check)
            if missing:
                raise serializers.ValidationError({
                    "context": {
                        field: "This field is required by instrument config."
                        for field in missing
                    }
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> Measurement:
        """Atomically create Measurement + optional MeasurementContext."""
        context_data = validated_data.pop("_context_input", None)
        measurement = super().create(validated_data)

        if context_data:
            MeasurementContext.objects.create(
                measurement=measurement,
                instrument=measurement.instrument,
                operator=context_data.get("operator", ""),
                lot_number=context_data.get("lot_number", ""),
                method=context_data.get("method", ""),
                sample_id=context_data.get("sample_id", ""),
                notes=context_data.get("notes", ""),
            )
            # Refresh so the read-only `context` field is populated on the response
            measurement.refresh_from_db()

        return measurement
