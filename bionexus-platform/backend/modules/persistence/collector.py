"""BioNexus Collector — Serial port listener.

Watches USB/serial ports for instrument data,
parses it, and writes to the local WAL (PendingMeasurement).
"""

import hashlib
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import serial
import serial.tools.list_ports

logger = logging.getLogger("persistence.collector")

BAUD_RATE = int(os.getenv("SERIAL_BAUD_RATE", "9600"))
READ_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", "1.0"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2.0"))


def compute_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    parts = line.split()
    if len(parts) >= 2:
        try:
            value = float(parts[0])
            unit = parts[1]
            return {"value": value, "unit": unit, "raw": line}
        except ValueError:
            pass
    return None


def write_to_wal(parsed: dict, port: str) -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "core.settings"
    )
    import django
    if not django.apps.registry.apps.ready:
        django.setup()

    from modules.persistence.models import PendingMeasurement
    from django.utils import timezone as dj_timezone

    now = dj_timezone.now()
    raw = parsed["raw"]
    data_hash = compute_hash(raw)

    PendingMeasurement.objects.create(
        idempotency_key=uuid.uuid4(),
        sample_id=1,
        instrument_id=1,
        parameter="measurement",
        value=parsed["value"],
        unit=parsed["unit"],
        data_hash=data_hash,
        source_timestamp=now,
        hub_received_at=now,
        sync_status="pending",
    )
    logger.info(
        "WAL write: value=%s unit=%s hash=%s port=%s",
        parsed["value"], parsed["unit"], data_hash[:16], port
    )


def scan_ports() -> list[str]:
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


def run_collector() -> None:
    logger.info("BioNexus Collector starting...")
    open_ports: dict[str, serial.Serial] = {}

    while True:
        available = scan_ports()

        for port in available:
            if port not in open_ports:
                try:
                    ser = serial.Serial(
                        port, BAUD_RATE, timeout=READ_TIMEOUT
                    )
                    open_ports[port] = ser
                    logger.info("Instrument detected on %s", port)
                except serial.SerialException as e:
                    logger.warning("Cannot open %s: %s", port, e)

        for port in list(open_ports.keys()):
            if port not in available:
                open_ports[port].close()
                del open_ports[port]
                logger.info("Instrument disconnected from %s", port)
                continue

            try:
                line = open_ports[port].readline().decode(
                    "utf-8", errors="replace"
                )
                parsed = parse_line(line)
                if parsed:
                    write_to_wal(parsed, port)
            except serial.SerialException as e:
                logger.error("Read error on %s: %s", port, e)
                open_ports[port].close()
                del open_ports[port]

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collector()
