"""Views for the persistence (WAL) module.

CaptureView  — Hub writes measurement to local WAL (always available, even offline)
IngestView   — SyncEngine posts batch to server, receives per-item ACKs
PendingListView — Debug/admin listing of pending WAL records
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import AuditTrail

from .models import PendingMeasurement
from .serializers import (
    CaptureSerializer,
    IngestItemSerializer,
    IngestResponseItemSerializer,
    PendingMeasurementSerializer,
)
from .sync_engine import _get_config


class CaptureView(APIView):
    """POST /api/persistence/capture/

    Hub sends a measurement here FIRST (before any network attempt to the
    server). This writes to the local WAL (SQLite) and is always available.

    Idempotent: if the idempotency_key already exists, returns the existing
    record with HTTP 200 instead of 201.
    """

    def post(self, request):
        serializer = CaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Idempotent check
        existing = PendingMeasurement.objects.filter(
            idempotency_key=data["idempotency_key"]
        ).first()

        if existing:
            return Response(
                PendingMeasurementSerializer(existing).data,
                status=status.HTTP_200_OK,
            )

        record = PendingMeasurement.objects.create(
            idempotency_key=data["idempotency_key"],
            sample_id=data["sample_id"],
            instrument_id=data["instrument_id"],
            parameter=data["parameter"],
            value=data["value"],
            unit=data["unit"],
            data_hash=data["data_hash"],
            source_timestamp=data["source_timestamp"],
            hub_received_at=data["hub_received_at"],
            sync_status="pending",
        )

        return Response(
            PendingMeasurementSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class IngestView(APIView):
    """POST /api/persistence/ingest/

    SyncEngine sends a batch of measurements. For each item:
    1. Check idempotency_key → if exists: return "duplicate" ACK
    2. Create Measurement + AuditTrail entry
    3. Preserve original data_hash (bypass auto-compute)
    4. Calculate clock_drift_ms = (server_now - hub_received_at)
    5. Return per-item ACK with confirmation_hash
    """

    def post(self, request):
        # Accept list of items
        serializer = IngestItemSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data

        from modules.measurements.models import Measurement

        drift_threshold = _get_config("CLOCK_DRIFT_THRESHOLD_MS", 5000)
        server_now = timezone.now()
        acks = []

        for item in items:
            idem_key = str(item["idempotency_key"])

            # Idempotent: check existing Measurement
            existing = Measurement.objects.filter(
                idempotency_key=idem_key
            ).first()

            if existing:
                acks.append({
                    "idempotency_key": idem_key,
                    "measurement_id": existing.pk,
                    "confirmation_hash": existing.data_hash,
                    "server_received_at": server_now.isoformat(),
                    "clock_drift_ms": 0,
                    "drift_flagged": False,
                    "status": "duplicate",
                })
                continue

            # Parse timestamps
            source_ts = item["source_timestamp"]
            hub_ts = item["hub_received_at"]

            with transaction.atomic():
                measurement = Measurement(
                    sample_id=item["sample_id"],
                    instrument_id=item["instrument_id"],
                    parameter=item["parameter"],
                    value=Decimal(str(item["value"])),
                    unit=item["unit"],
                    measured_at=source_ts,
                    idempotency_key=idem_key,
                )
                measurement.save()

                # Preserve original data_hash (bypass auto-compute)
                Measurement.objects.filter(pk=measurement.pk).update(
                    data_hash=item["data_hash"]
                )

                # Audit trail
                AuditTrail.record(
                    entity_type="Measurement",
                    entity_id=measurement.pk,
                    operation="CREATE",
                    changes={
                        "source": "hub_sync",
                        "idempotency_key": idem_key,
                    },
                    snapshot_before={},
                    snapshot_after={
                        "parameter": item["parameter"],
                        "value": str(item["value"]),
                        "unit": item["unit"],
                        "source_timestamp": str(source_ts),
                        "data_hash": item["data_hash"],
                    },
                )

            # Clock drift
            drift_ms = int((server_now - hub_ts).total_seconds() * 1000)
            flagged = abs(drift_ms) > drift_threshold

            acks.append({
                "idempotency_key": idem_key,
                "measurement_id": measurement.pk,
                "confirmation_hash": item["data_hash"],
                "server_received_at": server_now.isoformat(),
                "clock_drift_ms": drift_ms,
                "drift_flagged": flagged,
                "status": "created",
            })

        return Response(acks, status=status.HTTP_200_OK)


class PendingListView(generics.ListAPIView):
    """GET /api/persistence/pending/

    Debug/admin endpoint listing WAL records. Supports filtering:
      ?sync_status=pending
      ?drift_flagged=true
    """

    serializer_class = PendingMeasurementSerializer

    def get_queryset(self):
        qs = PendingMeasurement.objects.all().order_by("created_at")

        sync_status = self.request.query_params.get("sync_status")
        if sync_status:
            qs = qs.filter(sync_status=sync_status)

        drift_flagged = self.request.query_params.get("drift_flagged")
        if drift_flagged is not None:
            qs = qs.filter(drift_flagged=drift_flagged.lower() == "true")

        return qs
