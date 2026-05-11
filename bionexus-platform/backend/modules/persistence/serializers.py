"""Serializers for the persistence (WAL) module."""

import uuid
from decimal import Decimal

from rest_framework import serializers

from .models import PendingMeasurement


class CaptureSerializer(serializers.Serializer):
    """Validates hub POST to /api/persistence/capture/.

    Accepts a single measurement or a list (many=True).
    Idempotent: if idempotency_key already exists, returns the existing record.
    """

    idempotency_key = serializers.UUIDField(required=True)
    sample_id = serializers.IntegerField(required=True)
    instrument_id = serializers.IntegerField(required=True)
    parameter = serializers.CharField(max_length=255, required=True)
    value = serializers.DecimalField(max_digits=20, decimal_places=10, required=True)
    unit = serializers.CharField(max_length=50, required=True)
    data_hash = serializers.CharField(max_length=64, required=True)
    source_timestamp = serializers.DateTimeField(required=True)
    hub_received_at = serializers.DateTimeField(required=True)


class IngestItemSerializer(serializers.Serializer):
    """Validates each item in a batch POST to /api/persistence/ingest/."""

    idempotency_key = serializers.UUIDField(required=True)
    sample_id = serializers.IntegerField(required=True)
    instrument_id = serializers.IntegerField(required=True)
    parameter = serializers.CharField(max_length=255, required=True)
    value = serializers.DecimalField(max_digits=20, decimal_places=10, required=True)
    unit = serializers.CharField(max_length=50, required=True)
    data_hash = serializers.CharField(max_length=64, required=True)
    source_timestamp = serializers.DateTimeField(required=True)
    hub_received_at = serializers.DateTimeField(required=True)


class IngestResponseItemSerializer(serializers.Serializer):
    """Per-item ACK in the ingest response."""

    idempotency_key = serializers.UUIDField()
    measurement_id = serializers.IntegerField()
    confirmation_hash = serializers.CharField(max_length=64)
    server_received_at = serializers.DateTimeField()
    clock_drift_ms = serializers.IntegerField()
    drift_flagged = serializers.BooleanField()
    status = serializers.CharField()  # "created" or "duplicate"


class PendingMeasurementSerializer(serializers.ModelSerializer):
    """Read-only serializer for admin/debug listing of pending records."""

    class Meta:
        model = PendingMeasurement
        fields = "__all__"
