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

    Threshold enforcement (LBN-CONF-002):
      When the instrument has an InstrumentConfig with thresholds for the
      measured parameter, the serializer evaluates the verdict at validate-
      time:
        - "log"   : silent, captured as normal
        - "alert" : captured, response carries `threshold_verdict="alert"`
                    so the UI can render a warning banner
        - "block" : ValidationError 400, no measurement persisted
                    (supervisor re-auth bypass is a future feature)
    """

    # Read-only nested representation for GET
    context = MeasurementContextSerializer(read_only=True)
    # Write-only nested input for POST
    context_input = NestedContextInputSerializer(
        write_only=True, required=False, source="_context_input"
    )
    # Read-only verdict surfaced on create response (computed at validate-time)
    threshold_verdict = serializers.SerializerMethodField()

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
            "threshold_verdict",
        ]
        read_only_fields = ["id", "data_hash", "created_at"]

    def get_threshold_verdict(self, obj):
        """Surface the threshold verdict attached at create-time.

        Returns None on reads (we only compute the verdict during writes,
        because the threshold may have been re-configured since the
        measurement was captured ; the stored audit trail is the source
        of truth for retrospective verdicts).
        """
        return getattr(obj, "_threshold_verdict", None)

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
        """Run the two API-boundary checks: required metadata + thresholds.

        Required metadata (LBN-CONF-001): the instrument's InstrumentConfig
        can mark some MeasurementContext fields as mandatory. Missing
        fields produce a 400 with ``{"context": {field: msg}}``.

        Threshold enforcement (LBN-CONF-002): the same config can carry
        per-parameter rules. ``block`` verdict raises 400 immediately
        (no measurement persisted). ``alert``/``log`` verdicts are stashed
        on attrs so ``create()`` can carry them onto the response.
        """
        instrument = attrs.get("instrument")
        context_data = attrs.get("_context_input")

        if instrument and hasattr(instrument, "config"):
            config = instrument.config

            # 1. Required metadata fields
            to_check = context_data or {}
            missing = config.validate_context(to_check)
            if missing:
                raise serializers.ValidationError({
                    "context": {
                        field: "This field is required by instrument config."
                        for field in missing
                    }
                })

            # 2. Threshold rules
            parameter = attrs.get("parameter")
            value = attrs.get("value")
            if parameter and value is not None:
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    # Non-numeric value: skip threshold eval (e.g., textual
                    # qualitative results), keep the rest of validation intact.
                    numeric_value = None

                if numeric_value is not None:
                    verdict = config.evaluate_threshold(parameter, numeric_value)
                    if verdict == "block":
                        raise serializers.ValidationError({
                            "value": (
                                f"Value {numeric_value} violates the block threshold "
                                f"configured for parameter '{parameter}' on this "
                                f"instrument. Supervisor override is required to "
                                f"persist out-of-spec readings."
                            ),
                            "threshold_verdict": "block",
                        })
                    # alert and log verdicts ride along to the response
                    attrs["_threshold_verdict"] = verdict

        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> Measurement:
        """Atomically create Measurement + optional MeasurementContext."""
        context_data = validated_data.pop("_context_input", None)
        threshold_verdict = validated_data.pop("_threshold_verdict", None)

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

        # Stash on the instance so get_threshold_verdict() surfaces it
        # on this exact response, without persisting in DB.
        if threshold_verdict is not None:
            measurement._threshold_verdict = threshold_verdict

        return measurement
