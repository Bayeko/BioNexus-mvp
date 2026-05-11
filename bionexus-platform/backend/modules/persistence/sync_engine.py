"""Sync engine: BackoffCalculator, CongestionController, SyncEngine.

Handles retry with exponential backoff, adaptive batch sizing,
burst limiting, and end-to-end ACK verification.
"""

import logging
import random
import signal
import time
from decimal import Decimal
from typing import Any, Callable

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PendingMeasurement

logger = logging.getLogger("persistence.sync")


def _get_config(key: str, default: Any = None) -> Any:
    """Get a persistence config value from settings.PERSISTENCE."""
    conf = getattr(settings, "PERSISTENCE", {})
    return conf.get(key, default)


class BackoffCalculator:
    """Exponential backoff with jitter to prevent thundering herd."""

    def __init__(
        self,
        base_s: float | None = None,
        max_s: float | None = None,
        jitter_s: float | None = None,
    ):
        self.base_s = base_s if base_s is not None else _get_config("BACKOFF_BASE_S", 1.0)
        self.max_s = max_s if max_s is not None else _get_config("BACKOFF_MAX_S", 300.0)
        self.jitter_s = jitter_s if jitter_s is not None else _get_config("BACKOFF_JITTER_S", 0.5)

    def delay_for(self, retry_count: int) -> float:
        """Calculate delay: min(base * 2^retry + jitter, max)."""
        exponential = self.base_s * (2 ** retry_count)
        jitter = random.uniform(0, self.jitter_s)
        return min(exponential + jitter, self.max_s)


class CongestionController:
    """Adaptive batch sizing and burst limiting for reconnection scenarios."""

    def __init__(
        self,
        initial_batch_size: int | None = None,
        min_batch_size: int = 5,
        max_batch_size: int = 100,
        batch_delay_ms: int | None = None,
        server_slow_ms: int | None = None,
        server_fast_ms: int | None = None,
        max_burst_per_minute: int | None = None,
    ):
        self.current_batch_size = initial_batch_size or _get_config("BATCH_SIZE", 50)
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.batch_delay_ms = batch_delay_ms or _get_config("BATCH_DELAY_MS", 500)
        self.server_slow_ms = server_slow_ms or _get_config("SERVER_SLOW_MS", 2000)
        self.server_fast_ms = server_fast_ms or _get_config("SERVER_FAST_MS", 500)
        self.max_burst_per_minute = max_burst_per_minute or _get_config("MAX_BURST_PER_MINUTE", 200)

        self._sent_this_minute = 0
        self._minute_start = time.monotonic()

    def adjust(self, response_time_ms: float) -> None:
        """Adapt batch size based on server response time."""
        if response_time_ms > self.server_slow_ms:
            self.current_batch_size = max(
                self.min_batch_size, self.current_batch_size // 2
            )
            logger.info(
                "Server slow (%.0fms), batch size → %d",
                response_time_ms, self.current_batch_size,
            )
        elif response_time_ms < self.server_fast_ms:
            self.current_batch_size = min(
                self.max_batch_size, self.current_batch_size * 2
            )
            logger.info(
                "Server fast (%.0fms), batch size → %d",
                response_time_ms, self.current_batch_size,
            )

    def next_batch_size(self) -> int:
        """Return batch size clamped by burst budget remaining this minute."""
        self._maybe_reset_minute()
        remaining = self.max_burst_per_minute - self._sent_this_minute
        if remaining <= 0:
            return 0
        return min(self.current_batch_size, remaining)

    def delay_between_batches(self) -> float:
        """Return seconds to sleep between batches."""
        return self.batch_delay_ms / 1000.0

    def record_sent(self, count: int) -> None:
        """Track burst count for this minute window."""
        self._maybe_reset_minute()
        self._sent_this_minute += count

    def _maybe_reset_minute(self) -> None:
        now = time.monotonic()
        if now - self._minute_start >= 60.0:
            self._sent_this_minute = 0
            self._minute_start = now


class SyncEngine:
    """Orchestrates sync from local WAL to server.

    Supports two transport modes:
    - "direct": calls the ingest logic in-process (for MVP/SQLite)
    - "http": POSTs to the server URL (for distributed deployments)
    """

    def __init__(self, transport: Callable | None = None):
        """Initialize sync engine.

        Args:
            transport: Callable that accepts a list of measurement dicts
                       and returns a list of ACK dicts. If None, uses
                       the default direct transport.
        """
        self.backoff = BackoffCalculator()
        self.congestion = CongestionController()
        self.transport = transport or self._direct_transport
        self._shutdown_requested = False

    def run_once(self) -> dict:
        """Single sync pass. Returns stats dict."""
        stats = {"synced": 0, "failed": 0, "skipped": 0}

        batch_size = self.congestion.next_batch_size()
        if batch_size <= 0:
            logger.info("Burst limit reached, waiting for next minute window")
            stats["skipped"] = 1
            return stats

        records = self._pick_batch(batch_size)
        if not records:
            return stats

        # Mark as syncing
        pks = [r.pk for r in records]
        PendingMeasurement.objects.filter(pk__in=pks).update(sync_status="syncing")

        try:
            payloads = [r.to_measurement_payload() for r in records]
            start_ms = time.monotonic() * 1000
            acks = self.transport(payloads)
            elapsed_ms = time.monotonic() * 1000 - start_ms

            self.congestion.adjust(elapsed_ms)
            synced, failed = self._process_acks(records, acks)
            self.congestion.record_sent(synced)

            stats["synced"] = synced
            stats["failed"] = failed
        except Exception as e:
            logger.error("Sync batch failed: %s", e)
            self._handle_failure(records, str(e))
            stats["failed"] = len(records)

        return stats

    def run_loop(self, max_iterations: int | None = None) -> None:
        """Continuous sync loop with graceful shutdown."""
        self._shutdown_requested = False
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        def _handle_signal(signum, frame):
            logger.info("Shutdown signal received, finishing current batch...")
            self._shutdown_requested = True

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        iterations = 0
        try:
            while not self._shutdown_requested:
                if max_iterations is not None and iterations >= max_iterations:
                    break

                stats = self.run_once()
                iterations += 1

                if stats["synced"] == 0 and stats["failed"] == 0:
                    # Nothing to sync, sleep longer
                    time.sleep(2.0)
                else:
                    time.sleep(self.congestion.delay_between_batches())
        finally:
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)

        logger.info("Sync loop exited after %d iterations", iterations)

    def _pick_batch(self, batch_size: int) -> list[PendingMeasurement]:
        """Select records eligible for sync (pending or failed with backoff elapsed)."""
        now = timezone.now()
        eligible = []

        candidates = (
            PendingMeasurement.objects
            .filter(sync_status__in=["pending", "failed"])
            .order_by("created_at")[:batch_size * 2]  # over-fetch to filter retries
        )

        for record in candidates:
            if len(eligible) >= batch_size:
                break

            if record.sync_status == "pending":
                eligible.append(record)
            elif record.sync_status == "failed":
                delay = self.backoff.delay_for(record.retry_count)
                seconds_since_update = (now - record.updated_at).total_seconds()
                if seconds_since_update >= delay:
                    eligible.append(record)

        return eligible

    def _process_acks(
        self,
        records: list[PendingMeasurement],
        acks: list[dict],
    ) -> tuple[int, int]:
        """Match ACKs to records by idempotency_key, verify and update."""
        ack_map = {str(a["idempotency_key"]): a for a in acks}
        synced = 0
        failed = 0

        for record in records:
            key = str(record.idempotency_key)
            ack = ack_map.get(key)

            if not ack:
                record.sync_status = "failed"
                record.retry_count += 1
                record.last_error = "No ACK received for this record"
                record.save(update_fields=[
                    "sync_status", "retry_count", "last_error", "updated_at",
                ])
                failed += 1
                continue

            # Verify confirmation_hash matches our original data_hash
            if ack.get("confirmation_hash") != record.data_hash:
                record.sync_status = "failed"
                record.retry_count += 1
                record.last_error = (
                    f"Hash mismatch: expected {record.data_hash}, "
                    f"got {ack.get('confirmation_hash')}"
                )
                record.save(update_fields=[
                    "sync_status", "retry_count", "last_error", "updated_at",
                ])
                failed += 1
                continue

            # ACK verified — mark as synced
            record.sync_status = "synced"
            record.synced_measurement_id = ack.get("measurement_id")
            record.server_received_at = ack.get("server_received_at")
            record.clock_drift_ms = ack.get("clock_drift_ms")
            record.drift_flagged = ack.get("drift_flagged", False)
            record.save(update_fields=[
                "sync_status", "synced_measurement_id", "server_received_at",
                "clock_drift_ms", "drift_flagged", "updated_at",
            ])
            synced += 1

        return synced, failed

    def _handle_failure(
        self,
        records: list[PendingMeasurement],
        error: str,
    ) -> None:
        """Mark all records in batch as failed."""
        for record in records:
            record.sync_status = "failed"
            record.retry_count += 1
            record.last_error = error
            record.save(update_fields=[
                "sync_status", "retry_count", "last_error", "updated_at",
            ])

    @staticmethod
    def _direct_transport(payloads: list[dict]) -> list[dict]:
        """In-process transport: calls ingest logic directly (no HTTP).

        Used for MVP/single-machine deployments with SQLite.
        """
        from modules.measurements.models import Measurement
        from core.audit import AuditTrail

        drift_threshold = _get_config("CLOCK_DRIFT_THRESHOLD_MS", 5000)
        server_now = timezone.now()
        acks = []

        for payload in payloads:
            idem_key = payload["idempotency_key"]

            # Check for existing (idempotent)
            existing = Measurement.objects.filter(idempotency_key=idem_key).first()
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

            # Create Measurement
            from django.utils.dateparse import parse_datetime
            source_ts = payload["source_timestamp"]
            if isinstance(source_ts, str):
                source_ts = parse_datetime(source_ts)

            hub_ts = payload["hub_received_at"]
            if isinstance(hub_ts, str):
                hub_ts = parse_datetime(hub_ts)

            with transaction.atomic():
                measurement = Measurement(
                    sample_id=payload["sample_id"],
                    instrument_id=payload["instrument_id"],
                    parameter=payload["parameter"],
                    value=Decimal(payload["value"]),
                    unit=payload["unit"],
                    measured_at=source_ts,
                    idempotency_key=idem_key,
                )
                measurement.save()

                # Preserve original data_hash (bypass auto-compute)
                Measurement.objects.filter(pk=measurement.pk).update(
                    data_hash=payload["data_hash"]
                )

                # Record audit trail
                AuditTrail.record(
                    entity_type="Measurement",
                    entity_id=measurement.pk,
                    operation="CREATE",
                    changes={"source": "hub_sync", "idempotency_key": idem_key},
                    snapshot_before={},
                    snapshot_after={
                        "parameter": payload["parameter"],
                        "value": payload["value"],
                        "unit": payload["unit"],
                        "source_timestamp": str(source_ts),
                        "data_hash": payload["data_hash"],
                    },
                )

            # Clock drift
            drift_ms = int((server_now - hub_ts).total_seconds() * 1000)
            flagged = abs(drift_ms) > drift_threshold

            acks.append({
                "idempotency_key": idem_key,
                "measurement_id": measurement.pk,
                "confirmation_hash": payload["data_hash"],
                "server_received_at": server_now.isoformat(),
                "clock_drift_ms": drift_ms,
                "drift_flagged": flagged,
                "status": "created",
            })

        return acks
