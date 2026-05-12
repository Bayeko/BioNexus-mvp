"""Mock Vault HTTP server — run via ``python manage.py veeva_mock_server``.

A standalone stdlib-only server that imitates the subset of the real
Veeva Vault REST API that LBN pushes against. Listens on
``http://0.0.0.0:8001`` by default; everything is configurable via
flags.

Endpoints implemented:

  POST /api/v23.1/auth
       → returns a fake ``sessionId``

  POST /api/v23.1/vobjects/quality_event__v
       → accepts JSON, persists to ``mock_objects.json``, returns
         ``{ "id": "VVQE-<uuid8>", "responseStatus": "SUCCESS" }``

  POST /api/v23.1/objects/documents
       → multipart upload (metadata + binary), persists metadata to
         ``mock_objects.json`` + file to ``./mock_uploads/``, returns
         ``{ "id": "VVDOC-<uuid8>", "responseStatus": "SUCCESS" }``

  GET  /api/v23.1/vobjects/quality_event__v
       → list of all received objects (for debugging / demos)

  GET  /healthz
       → 200 OK + {"server":"veeva-mock"}

Failure injection: set ``VEEVA_MOCK_FAIL_RATE`` env var (0.0..1.0). On
each request, with that probability, the server returns a 500 + body
``{"responseStatus":"FAILURE","errorMessage":"injected"}`` so the
retry/DLQ path can be demoed.
"""

from __future__ import annotations

import json
import os
import random
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from django.core.management.base import BaseCommand


# ---------------------------------------------------------------------------
# Persistence — a single JSON file keeps it dumb, debuggable, and demoable.
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()


def _state_dir() -> Path:
    path = Path(os.environ.get("VEEVA_MOCK_STATE_DIR", "./mock_vault_state"))
    path.mkdir(parents=True, exist_ok=True)
    (path / "uploads").mkdir(exist_ok=True)
    return path


def _state_file() -> Path:
    return _state_dir() / "objects.json"


def _load_state() -> dict:
    f = _state_file()
    if not f.exists():
        return {"quality_events": [], "documents": []}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"quality_events": [], "documents": []}


def _save_state(state: dict) -> None:
    _state_file().write_text(
        json.dumps(state, indent=2, sort_keys=True), encoding="utf-8"
    )


def _append_object(kind: str, obj: dict) -> None:
    with _LOCK:
        state = _load_state()
        state.setdefault(kind, []).append(obj)
        _save_state(state)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class _MockVaultHandler(BaseHTTPRequestHandler):
    server_version = "VeevaMock/0.1"

    # Quiet the default access-log; we use a tighter format below.
    def log_message(self, format: str, *args) -> None:  # noqa: A002, ARG002
        # ASCII only — Windows cp1252 stdout would crash on non-ASCII glyphs.
        try:
            sys.stdout.write(
                f"[{datetime.utcnow().isoformat()}Z] "
                f"{self.command} {self.path} -> "
                f"{args[1] if len(args) > 1 else '?'}\n"
            )
            sys.stdout.flush()
        except Exception:
            # Never let a logging hiccup take down a handler.
            pass

    # -- routing ---------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._json(200, {"server": "veeva-mock", "ok": True})
            return
        if self.path == "/api/v23.1/vobjects/quality_event__v":
            self._json(200, _load_state().get("quality_events", []))
            return
        self._json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        if self._should_inject_failure():
            self._json(500, {
                "responseStatus": "FAILURE",
                "errorMessage": "injected by VEEVA_MOCK_FAIL_RATE",
            })
            return

        if self.path == "/api/v23.1/auth":
            self._json(200, {
                "responseStatus": "SUCCESS",
                "sessionId": f"mock-session-{uuid.uuid4().hex[:16]}",
            })
            return

        if self.path == "/api/v23.1/vobjects/quality_event__v":
            payload = self._read_json()
            if payload is None:
                self._json(400, {"responseStatus": "FAILURE", "errorMessage": "bad json"})
                return
            vault_id = f"VVQE-{uuid.uuid4().hex[:10].upper()}"
            _append_object("quality_events", {
                "id": vault_id,
                "received_at": datetime.utcnow().isoformat() + "Z",
                "payload": payload,
            })
            self._json(201, {"id": vault_id, "responseStatus": "SUCCESS"})
            return

        if self.path == "/api/v23.1/objects/documents":
            ok, meta_payload, file_bytes, content_type = self._read_multipart()
            if not ok:
                self._json(400, {
                    "responseStatus": "FAILURE",
                    "errorMessage": "multipart parse failed",
                })
                return
            vault_id = f"VVDOC-{uuid.uuid4().hex[:10].upper()}"
            # Persist the binary blob too so the demo can show "Vault has it".
            uploads = _state_dir() / "uploads"
            (uploads / f"{vault_id}.bin").write_bytes(file_bytes)
            _append_object("documents", {
                "id": vault_id,
                "received_at": datetime.utcnow().isoformat() + "Z",
                "metadata": meta_payload,
                "size_bytes": len(file_bytes),
                "content_type": content_type,
            })
            self._json(201, {"id": vault_id, "responseStatus": "SUCCESS"})
            return

        self._json(404, {"error": "not_found", "path": self.path})

    # -- helpers ---------------------------------------------------------

    def _should_inject_failure(self) -> bool:
        try:
            rate = float(os.environ.get("VEEVA_MOCK_FAIL_RATE", "0"))
        except ValueError:
            return False
        return random.random() < rate

    def _json(self, status: int, body: object) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _read_multipart(self) -> tuple[bool, dict, bytes, str]:
        """Very lightweight multipart parser. Good enough for the mock.

        Returns (ok, metadata_json, file_bytes, file_content_type).
        """
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return False, {}, b"", ""
        # Extract boundary
        try:
            boundary = content_type.split("boundary=", 1)[1].strip().encode("latin-1")
        except IndexError:
            return False, {}, b"", ""
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        parts = body.split(b"--" + boundary)
        meta_payload: dict = {}
        file_bytes = b""
        file_ct = ""
        for part in parts:
            part = part.strip(b"\r\n-")
            if not part or part.startswith(b"--"):
                continue
            try:
                header_blob, content = part.split(b"\r\n\r\n", 1)
            except ValueError:
                continue
            content = content.rstrip(b"\r\n-")
            headers_text = header_blob.decode("latin-1", errors="ignore").lower()
            if 'name="metadata"' in headers_text:
                try:
                    meta_payload = json.loads(content.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            elif 'name="file"' in headers_text:
                file_bytes = content
                for line in headers_text.splitlines():
                    if line.startswith("content-type:"):
                        file_ct = line.split(":", 1)[1].strip()
                        break
        return True, meta_payload, file_bytes, file_ct


# ---------------------------------------------------------------------------
# manage.py command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Run a stdlib HTTP server that imitates the Veeva Vault REST endpoints "
        "BioNexus pushes against. Used for FL Basel demo + local dev."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=8001)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe the mock state file before starting.",
        )

    def handle(self, *args, **options) -> None:
        host = options["host"]
        port = options["port"]

        if options["reset"]:
            f = _state_file()
            if f.exists():
                f.unlink()
            self.stdout.write(self.style.WARNING(f"Reset {f}"))

        _state_dir()  # ensure directory exists

        server = ThreadingHTTPServer((host, port), _MockVaultHandler)
        rate = os.environ.get("VEEVA_MOCK_FAIL_RATE", "0")
        self.stdout.write(self.style.SUCCESS(
            f"VEEVA MOCK Vault listening on http://{host}:{port}  "
            f"(fail_rate={rate}, state_dir={_state_dir()})"
        ))
        self.stdout.write(
            "Endpoints:\n"
            f"  POST http://{host}:{port}/api/v23.1/auth\n"
            f"  POST http://{host}:{port}/api/v23.1/vobjects/quality_event__v\n"
            f"  POST http://{host}:{port}/api/v23.1/objects/documents\n"
            f"  GET  http://{host}:{port}/api/v23.1/vobjects/quality_event__v\n"
            f"  GET  http://{host}:{port}/healthz\n"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopping mock Vault.")
            server.shutdown()
