#!/usr/bin/env python3
"""BioNexus Box Collector — Gateway bridge between lab instruments and cloud.

Listens on RS232/USB (or TCP socket for demo) for instrument data,
parses it, computes SHA-256 integrity hash that covers BOTH the raw
reading AND the operational context (operator, lot, method, instrument),
and POSTs to the BioNexus cloud API via /api/persistence/capture/.

Offline-safe: if the cloud is unreachable, measurements are stored in
a local SQLite queue and retried with exponential backoff on reconnect.

---------------------------------------------------------------------------
SHA-256 scope (LBN-CONF-001 decision):
    hash = SHA256({
        value, unit, source_timestamp,
        instrument_id, sample_id,
        operator, lot_number, method
    })
The hash binds the measurement to its CONTEXT, not just the raw value.
Any tampering with either the reading or the metadata breaks the hash.
---------------------------------------------------------------------------

Usage:
    # TCP demo, with operational context
    python box_collector.py --mode tcp --port 9600 \
        --operator OP-042 --lot-number LOT-2026-04 --method "USP <621>"

    # Serial (production), with custom API
    python box_collector.py --mode serial --device /dev/ttyUSB0 --baud 9600 \
        --api-url https://cloud.bionexus.ch --operator OP-042
"""

import argparse
import hashlib
import json
import logging
import os
import re
import signal
import socket
import sqlite3
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("BIONEXUS_API_URL", "http://localhost:8000")
CAPTURE_ENDPOINT = "/api/persistence/capture/"
DEVICE_ID = os.getenv("BIONEXUS_DEVICE_ID", "box-gateway-001")

# SQLite offline queue
DB_PATH = os.getenv("BIONEXUS_QUEUE_DB", "/var/lib/bionexus/queue.db")
if not os.path.isdir(os.path.dirname(DB_PATH)):
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue.db")

# Retry settings
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 300.0
BACKOFF_JITTER_S = 0.5
MAX_RETRIES = 10
SYNC_INTERVAL_S = 5.0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("box_collector")

# Graceful shutdown
_shutdown = threading.Event()


def _signal_handler(sig, frame):
    log.info("Shutdown signal received, finishing current work...")
    _shutdown.set()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ---------------------------------------------------------------------------
# Context + Reading dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CaptureContext:
    """Operational context attached at capture time.

    Mirrors the server-side MeasurementContext model. Fields are optional
    by default; enforcement of "required" fields happens server-side against
    the instrument's InstrumentConfig.
    """
    instrument_id: int = 0
    sample_id: int = 0
    operator: str = ""
    lot_number: str = ""
    method: str = ""
    external_sample_id: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedReading:
    """Raw output of a parser — the instrument-side part of the measurement."""
    parameter: str
    value: str
    unit: str
    source_timestamp: str  # ISO8601 UTC
    raw: str               # Original instrument line, verbatim
    protocol_meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SHA-256 — binds reading + context together
# ---------------------------------------------------------------------------

def compute_capture_hash(reading: ParsedReading, context: CaptureContext) -> str:
    """Compute SHA-256 over reading + context, in a canonical form.

    Per LBN-CONF-001: the hash must cover the full capture (not just value),
    so that any tampering with the operator, lot, method, instrument,
    or the reading itself invalidates the hash.

    Canonical form: JSON with sorted keys, no whitespace. This guarantees
    the Box, server, and any re-verifier compute the same hash byte-for-byte.
    """
    canonical = {
        "value": str(reading.value),
        "unit": reading.unit,
        "parameter": reading.parameter,
        "source_timestamp": reading.source_timestamp,
        "instrument_id": int(context.instrument_id),
        "sample_id": int(context.sample_id),
        "operator": context.operator or "",
        "lot_number": context.lot_number or "",
        "method": context.method or "",
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Parsers — BaseParser contract + Mettler SICS, Sartorius SBI, Generic CSV
# ---------------------------------------------------------------------------

class BaseParser(ABC):
    """Abstract base for instrument protocol parsers.

    Each concrete parser must implement:
      - can_parse(line) → bool
      - extract(line)   → ParsedReading | None   (raw extraction, no context)

    The base class provides parse() that orchestrates extraction, context
    enrichment, and hash computation — so every parser emits the same
    payload shape.
    """

    name: str = "base"
    protocol: str = "base"

    @classmethod
    @abstractmethod
    def can_parse(cls, line: str) -> bool: ...

    @classmethod
    @abstractmethod
    def extract(cls, line: str) -> Optional[ParsedReading]: ...

    @classmethod
    def parse(
        cls,
        line: str,
        context: CaptureContext,
    ) -> Optional[dict]:
        """Parse a line into a fully-formed capture payload.

        Returns a dict shaped for:
          - the local SQLite offline queue
          - the cloud /api/persistence/capture/ endpoint
          - the cloud MeasurementContext enrichment

        Shape:
            {
              idempotency_key, sample_id, instrument_id,
              parameter, value, unit,
              source_timestamp, hub_received_at,
              raw, data_hash,
              context: { operator, lot_number, method, sample_id (external), notes },
              protocol_meta: { protocol, stability, ... }
            }
        """
        reading = cls.extract(line)
        if reading is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        data_hash = compute_capture_hash(reading, context)

        return {
            "idempotency_key": str(uuid.uuid4()),
            "sample_id": context.sample_id,
            "instrument_id": context.instrument_id,
            "parameter": reading.parameter,
            "value": reading.value,
            "unit": reading.unit,
            "source_timestamp": reading.source_timestamp,
            "hub_received_at": now,
            "raw": reading.raw,
            "data_hash": data_hash,
            "context": {
                "operator": context.operator,
                "lot_number": context.lot_number,
                "method": context.method,
                "sample_id": context.external_sample_id,
                "notes": context.notes,
                "instrument_id": context.instrument_id,
            },
            "protocol_meta": {
                "protocol": cls.protocol,
                "parser": cls.name,
                **reading.protocol_meta,
            },
        }


class MettlerSICSParser(BaseParser):
    """Parse Mettler Toledo SICS (Standard Interface Command Set) responses.

    Typical balance output:
        S S     12.3456 g       (stable weight)
        S D     12.3400 g       (dynamic/unstable weight)
        ES                       (error: overload, etc.)

    Format: <status> <stability> <value> <unit>
    """

    name = "mettler_sics_v1"
    protocol = "SICS"

    PATTERN = re.compile(r"^([A-Z]+)\s+([A-Z])\s+([-\d.]+)\s+(\S+)\s*$")

    @classmethod
    def can_parse(cls, line: str) -> bool:
        return bool(cls.PATTERN.match(line.strip()))

    @classmethod
    def extract(cls, line: str) -> Optional[ParsedReading]:
        m = cls.PATTERN.match(line.strip())
        if not m:
            return None

        cmd, stability, value_str, unit = m.groups()

        if cmd in ("ES", "EL", "ET"):  # Errors
            log.warning("Mettler error response: %s", line.strip())
            return None

        return ParsedReading(
            parameter="weight",
            value=value_str,
            unit=unit,
            source_timestamp=datetime.now(timezone.utc).isoformat(),
            raw=line.rstrip("\r\n"),
            protocol_meta={
                "command": cmd,
                "stability": "stable" if stability == "S" else "dynamic",
            },
        )


class SartoriusSBIParser(BaseParser):
    """Parse Sartorius SBI (Simple Balance Interface) output.

    Format: <stability><sign><value><unit><CR><LF>
    Example: +  100.0000 g
             -    5.1234 g
    """

    name = "sartorius_sbi_v1"
    protocol = "SBI"

    PATTERN = re.compile(r"^([+-]?)\s*([\d.]+)\s+(\S+)\s*$")

    @classmethod
    def can_parse(cls, line: str) -> bool:
        return bool(cls.PATTERN.match(line.strip()))

    @classmethod
    def extract(cls, line: str) -> Optional[ParsedReading]:
        m = cls.PATTERN.match(line.strip())
        if not m:
            return None

        sign, value_str, unit = m.groups()
        if sign == "-":
            value_str = "-" + value_str

        return ParsedReading(
            parameter="weight",
            value=value_str,
            unit=unit,
            source_timestamp=datetime.now(timezone.utc).isoformat(),
            raw=line.rstrip("\r\n"),
            protocol_meta={"stability": "stable"},
        )


class GenericCSVParser(BaseParser):
    """Parse generic CSV instrument output.

    Format: <parameter>,<value>,<unit>
    Example: pH,7.42,pH
             temperature,25.1,°C
    """

    name = "generic_csv_v1"
    protocol = "CSV"

    @classmethod
    def can_parse(cls, line: str) -> bool:
        parts = line.strip().split(",")
        if len(parts) >= 3:
            try:
                float(parts[1])
                return True
            except ValueError:
                return False
        return False

    @classmethod
    def extract(cls, line: str) -> Optional[ParsedReading]:
        parts = line.strip().split(",")
        if len(parts) < 3:
            return None

        parameter = parts[0].strip()
        value_str = parts[1].strip()
        unit = parts[2].strip()

        try:
            float(value_str)
        except ValueError:
            return None

        return ParsedReading(
            parameter=parameter,
            value=value_str,
            unit=unit,
            source_timestamp=datetime.now(timezone.utc).isoformat(),
            raw=line.rstrip("\r\n"),
            protocol_meta={},
        )


# Parser dispatch — try each parser in order
PARSERS: list[type[BaseParser]] = [
    MettlerSICSParser,
    SartoriusSBIParser,
    GenericCSVParser,
]


def parse_line(line: str, context: CaptureContext) -> Optional[dict]:
    """Try all parsers, return first match's full capture payload."""
    for parser in PARSERS:
        if parser.can_parse(line):
            result = parser.parse(line, context)
            if result:
                log.info(
                    "Parsed [%s]: %s = %s %s (op=%s lot=%s hash=%s...)",
                    parser.name,
                    result["parameter"],
                    result["value"],
                    result["unit"],
                    context.operator or "-",
                    context.lot_number or "-",
                    result["data_hash"][:12],
                )
                return result
    log.warning("No parser matched line: %r", line.strip())
    return None


# ---------------------------------------------------------------------------
# SQLite Offline Queue
# ---------------------------------------------------------------------------

def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize local SQLite queue for offline buffering."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT UNIQUE NOT NULL,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            last_error TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_status
        ON pending_queue (status, created_at)
    """)
    conn.commit()
    log.info("SQLite queue initialized: %s (WAL mode)", db_path)
    return conn


def queue_measurement(conn: sqlite3.Connection, measurement: dict) -> None:
    """Store measurement in local offline queue."""
    payload = json.dumps(measurement, default=str)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO pending_queue (idempotency_key, payload) VALUES (?, ?)",
            (measurement["idempotency_key"], payload),
        )
        conn.commit()
        log.debug("Queued: %s", measurement["idempotency_key"][:8])
    except sqlite3.Error as e:
        log.error("SQLite queue error: %s", e)


def get_pending(conn: sqlite3.Connection, limit: int = 50) -> list:
    """Get pending measurements ready for sync."""
    cursor = conn.execute(
        """SELECT id, idempotency_key, payload, retry_count
           FROM pending_queue
           WHERE status IN ('pending', 'failed')
           ORDER BY created_at ASC
           LIMIT ?""",
        (limit,),
    )
    return cursor.fetchall()


def mark_synced(conn: sqlite3.Connection, row_id: int) -> None:
    conn.execute(
        "UPDATE pending_queue SET status='synced', updated_at=datetime('now') WHERE id=?",
        (row_id,),
    )
    conn.commit()


def mark_failed(conn: sqlite3.Connection, row_id: int, error: str) -> None:
    conn.execute(
        """UPDATE pending_queue
           SET status='failed', retry_count=retry_count+1,
               last_error=?, updated_at=datetime('now')
           WHERE id=?""",
        (error, row_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Cloud Sync — Push queued measurements to API
# ---------------------------------------------------------------------------

# Fields the server-side /api/persistence/capture/ endpoint accepts today.
# Anything outside this allow-list is stripped at send time to keep the
# existing endpoint contract stable. Context + protocol_meta are still
# preserved locally for audit and future server-side ingestion.
_CAPTURE_ALLOWED_KEYS = {
    "idempotency_key",
    "sample_id",
    "instrument_id",
    "parameter",
    "value",
    "unit",
    "data_hash",
    "source_timestamp",
    "hub_received_at",
}


def build_capture_payload(measurement: dict) -> dict:
    """Build the POST body the cloud endpoint currently accepts.

    Kept narrow to maintain backward compatibility with the existing
    /api/persistence/capture/ contract. Metadata travels via a separate
    call in a later sprint.
    """
    return {k: v for k, v in measurement.items() if k in _CAPTURE_ALLOWED_KEYS}


def push_to_cloud(api_url: str, measurement: dict) -> bool:
    """POST a single measurement to /api/persistence/capture/."""
    url = f"{api_url.rstrip('/')}{CAPTURE_ENDPOINT}"
    payload = build_capture_payload(measurement)

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Device-ID": DEVICE_ID,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            log.info(
                "  -> Cloud OK (%d): %s = %s %s",
                resp.status_code,
                measurement["parameter"],
                measurement["value"],
                measurement["unit"],
            )
            return True
        else:
            log.warning("  -> Cloud %d: %s", resp.status_code, resp.text[:200])
            return False
    except requests.exceptions.ConnectionError:
        log.warning("  -> Cloud OFFLINE — buffered locally")
        return False
    except requests.exceptions.Timeout:
        log.warning("  -> Cloud TIMEOUT — will retry")
        return False
    except Exception as e:
        log.error("  -> Cloud ERROR: %s", e)
        return False


def backoff_delay(retry_count: int) -> float:
    """Exponential backoff with jitter."""
    import random
    delay = min(BACKOFF_BASE_S * (2 ** retry_count), BACKOFF_MAX_S)
    jitter = random.uniform(-BACKOFF_JITTER_S, BACKOFF_JITTER_S)
    return max(0.1, delay + jitter)


def sync_loop(conn: sqlite3.Connection, api_url: str) -> None:
    """Background thread: push pending measurements to cloud."""
    log.info("Sync thread started (interval: %.1fs)", SYNC_INTERVAL_S)

    while not _shutdown.is_set():
        pending = get_pending(conn, limit=50)

        if pending:
            log.info("Syncing %d pending measurement(s)...", len(pending))

        for row_id, idem_key, payload_json, retry_count in pending:
            if _shutdown.is_set():
                break

            if retry_count > 0:
                delay = backoff_delay(retry_count)
                if retry_count > MAX_RETRIES:
                    log.error(
                        "Max retries (%d) exceeded for %s — dead-lettered",
                        MAX_RETRIES, idem_key[:8],
                    )
                    conn.execute(
                        "UPDATE pending_queue SET status='dead' WHERE id=?",
                        (row_id,),
                    )
                    conn.commit()
                    continue

            measurement = json.loads(payload_json)
            if push_to_cloud(api_url, measurement):
                mark_synced(conn, row_id)
            else:
                mark_failed(conn, row_id, "cloud_unreachable")

        _shutdown.wait(timeout=SYNC_INTERVAL_S)

    log.info("Sync thread stopped")


# ---------------------------------------------------------------------------
# Input Listeners — TCP Socket or Serial Port
# ---------------------------------------------------------------------------

def listen_tcp(
    port: int,
    context: CaptureContext,
    conn: sqlite3.Connection,
    api_url: str,
    db_path: str = "",
) -> None:
    """Listen for instrument data on TCP socket (demo mode)."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(1.0)
    server.bind(("0.0.0.0", port))
    server.listen(1)

    log.info("=" * 60)
    log.info("BioNexus Box Collector — TCP mode")
    log.info("Listening on port %d for instrument data...", port)
    log.info("API target: %s", api_url)
    log.info("Offline queue: %s", db_path)
    log.info(
        "Context: instrument=%d sample=%d operator=%s lot=%s method=%s",
        context.instrument_id, context.sample_id,
        context.operator or "-", context.lot_number or "-",
        context.method or "-",
    )
    log.info("=" * 60)

    while not _shutdown.is_set():
        try:
            client, addr = server.accept()
            log.info("Instrument connected from %s", addr)
            buffer = ""

            client.settimeout(1.0)
            while not _shutdown.is_set():
                try:
                    data = client.recv(1024)
                    if not data:
                        log.info("Instrument disconnected")
                        break

                    buffer += data.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        measurement = parse_line(line, context)
                        if measurement:
                            queue_measurement(conn, measurement)
                            if not push_to_cloud(api_url, measurement):
                                log.info(
                                    "  -> Buffered offline (%s)",
                                    measurement["idempotency_key"][:8],
                                )

                except socket.timeout:
                    continue
                except ConnectionResetError:
                    log.info("Instrument connection reset")
                    break

            client.close()

        except socket.timeout:
            continue
        except OSError:
            if _shutdown.is_set():
                break
            raise

    server.close()
    log.info("TCP listener stopped")


def listen_serial(
    device: str,
    baud: int,
    context: CaptureContext,
    conn: sqlite3.Connection,
    api_url: str,
    db_path: str = "",
) -> None:
    """Listen for instrument data on RS232/USB serial port (production)."""
    try:
        import serial
    except ImportError:
        log.error("pyserial required for serial mode: pip install pyserial")
        sys.exit(1)

    log.info("=" * 60)
    log.info("BioNexus Box Collector — Serial mode")
    log.info("Device: %s @ %d baud", device, baud)
    log.info("API target: %s", api_url)
    log.info("Offline queue: %s", db_path)
    log.info(
        "Context: instrument=%d sample=%d operator=%s lot=%s method=%s",
        context.instrument_id, context.sample_id,
        context.operator or "-", context.lot_number or "-",
        context.method or "-",
    )
    log.info("=" * 60)

    ser = serial.Serial(device, baud, timeout=1.0)
    log.info("Serial port open: %s", device)

    while not _shutdown.is_set():
        try:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            measurement = parse_line(line, context)
            if measurement:
                queue_measurement(conn, measurement)
                if not push_to_cloud(api_url, measurement):
                    log.info(
                        "  -> Buffered offline (%s)",
                        measurement["idempotency_key"][:8],
                    )

        except Exception as e:
            log.error("Serial read error: %s", e)
            time.sleep(1)

    ser.close()
    log.info("Serial listener stopped")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BioNexus Box Collector — Lab instrument gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode with operational context
  python box_collector.py --mode tcp --port 9600 \\
      --operator OP-042 --lot-number LOT-2026-04 --method "USP <621>"

  # Production (Mettler Toledo balance on USB)
  python box_collector.py --mode serial --device /dev/ttyUSB0 --baud 9600 \\
      --operator OP-042

  # Custom API endpoint
  python box_collector.py --mode tcp --port 9600 --api-url http://192.168.1.50:8000
        """,
    )

    parser.add_argument(
        "--mode", choices=["tcp", "serial"], default="tcp",
        help="Input mode: tcp (demo) or serial (production). Default: tcp",
    )
    parser.add_argument(
        "--port", type=int, default=9600,
        help="TCP port to listen on (tcp mode). Default: 9600",
    )
    parser.add_argument(
        "--device", default="/dev/ttyUSB0",
        help="Serial device path (serial mode). Default: /dev/ttyUSB0",
    )
    parser.add_argument(
        "--baud", type=int, default=9600,
        help="Serial baud rate. Default: 9600",
    )
    parser.add_argument(
        "--api-url", default=API_BASE_URL,
        help=f"BioNexus cloud API URL. Default: {API_BASE_URL}",
    )
    parser.add_argument(
        "--instrument-id", type=int, default=1,
        help="Instrument ID in BioNexus. Default: 1",
    )
    parser.add_argument(
        "--sample-id", type=int, default=1,
        help="Sample ID for measurements. Default: 1",
    )
    parser.add_argument(
        "--db", default=DB_PATH,
        help=f"SQLite queue path. Default: {DB_PATH}",
    )
    # --- Operational context (binds into SHA-256) ---
    parser.add_argument(
        "--operator", default="",
        help="Pseudonymized operator ID (e.g., OP-042). Binds into SHA-256.",
    )
    parser.add_argument(
        "--lot-number", default="",
        help="Lot/batch number under test. Binds into SHA-256.",
    )
    parser.add_argument(
        "--method", default="",
        help="Analytical method reference (e.g., 'USP <621>'). Binds into SHA-256.",
    )
    parser.add_argument(
        "--external-sample-id", default="",
        help="External QC sample ID (text). Stored in context, not in hash.",
    )
    parser.add_argument(
        "--notes", default="",
        help="Free-text operator notes. Stored in context, not in hash.",
    )

    args = parser.parse_args()

    db_path = args.db

    context = CaptureContext(
        instrument_id=args.instrument_id,
        sample_id=args.sample_id,
        operator=args.operator,
        lot_number=args.lot_number,
        method=args.method,
        external_sample_id=args.external_sample_id,
        notes=args.notes,
    )

    # Initialize SQLite offline queue
    conn = init_db(db_path)

    # Start background sync thread
    sync_thread = threading.Thread(
        target=sync_loop,
        args=(conn, args.api_url),
        daemon=True,
    )
    sync_thread.start()

    # Start listener
    try:
        if args.mode == "tcp":
            listen_tcp(args.port, context, conn, args.api_url, db_path)
        else:
            listen_serial(args.device, args.baud, context, conn, args.api_url, db_path)
    finally:
        _shutdown.set()
        sync_thread.join(timeout=5)
        conn.close()
        log.info("BioNexus Box Collector shut down cleanly")


if __name__ == "__main__":
    main()
