"""Generic multi-vendor mock LIMS server.

A single ``ThreadingHTTPServer`` exposes vendor-specific endpoint trees
on one port (default 8001). Each registered vendor declares its accepted
routes via :class:`VendorMockSpec`. The handler dispatches incoming
requests to the right spec by URL prefix.

Used by the ``lims_mock_server`` management command, see
``modules/integrations/base/management/commands/lims_mock_server.py``.
"""

from __future__ import annotations

import json
import os
import random
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Vendor registration
# ---------------------------------------------------------------------------

@dataclass
class VendorMockSpec:
    """Routes + ID prefix for one vendor on the unified mock server."""

    vendor: str                  # "veeva", "empower", ...
    url_prefix: str              # "/veeva", "/empower", ...
    object_routes: dict[str, str] = field(default_factory=dict)
    # object_routes maps "endpoint path (after url_prefix)" → "id prefix"
    # e.g. {"/api/v23.1/vobjects/quality_event__v": "VVQE"}
    document_routes: dict[str, str] = field(default_factory=dict)
    auth_routes: list[str] = field(default_factory=list)
    # Optional response envelope shape:
    #   "flat":     {"id": "...", "responseStatus": "SUCCESS"}
    #   "nested":   {"result": {"id": "..."}}
    response_envelope: str = "flat"


_REGISTRY: dict[str, VendorMockSpec] = {}
_LOCK = threading.Lock()


def register_vendor(spec: VendorMockSpec) -> None:
    _REGISTRY[spec.vendor] = spec


def registered_vendors() -> list[VendorMockSpec]:
    return list(_REGISTRY.values())


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _state_dir() -> Path:
    path = Path(os.environ.get("LIMS_MOCK_STATE_DIR", "./lims_mock_state"))
    path.mkdir(parents=True, exist_ok=True)
    (path / "uploads").mkdir(exist_ok=True)
    return path


def _state_file() -> Path:
    return _state_dir() / "objects.json"


def _load_state() -> dict:
    f = _state_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    _state_file().write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _append(vendor: str, kind: str, obj: dict) -> None:
    with _LOCK:
        state = _load_state()
        state.setdefault(vendor, {}).setdefault(kind, []).append(obj)
        _save_state(state)


def _list(vendor: str, kind: str) -> list:
    return _load_state().get(vendor, {}).get(kind, [])


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class MockLimsHandler(BaseHTTPRequestHandler):
    server_version = "LimsMock/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002, ARG002
        try:
            sys.stdout.write(
                f"[{datetime.utcnow().isoformat()}Z] "
                f"{self.command} {self.path} -> "
                f"{args[1] if len(args) > 1 else '?'}\n"
            )
            sys.stdout.flush()
        except Exception:
            pass

    # -- dispatch --------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._json(200, {"server": "lims-mock", "ok": True})
            return

        for spec in registered_vendors():
            if self.path.startswith(spec.url_prefix):
                sub = self.path[len(spec.url_prefix):]
                # Listing endpoint: GET on the same path returns recorded items.
                if sub in spec.object_routes:
                    self._json(200, _list(spec.vendor, "objects"))
                    return
                if sub in spec.document_routes:
                    self._json(200, _list(spec.vendor, "documents"))
                    return

        self._json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        if self._should_inject_failure():
            self._json(500, {
                "responseStatus": "FAILURE",
                "errorMessage": "injected by LIMS_MOCK_FAIL_RATE",
            })
            return

        for spec in registered_vendors():
            if not self.path.startswith(spec.url_prefix):
                continue
            sub = self.path[len(spec.url_prefix):]

            if sub in spec.auth_routes:
                self._json(200, _wrap(
                    spec, {"sessionId": f"mock-session-{uuid.uuid4().hex[:16]}"}
                ))
                return

            if sub in spec.object_routes:
                id_prefix = spec.object_routes[sub]
                payload = self._read_json()
                if payload is None:
                    self._json(400, _wrap(spec, {"errorMessage": "bad json"}, ok=False))
                    return
                obj_id = f"{id_prefix}-{uuid.uuid4().hex[:10].upper()}"
                _append(spec.vendor, "objects", {
                    "id": obj_id,
                    "received_at": datetime.utcnow().isoformat() + "Z",
                    "payload": payload,
                })
                self._json(201, _wrap(spec, {"id": obj_id}))
                return

            if sub in spec.document_routes:
                id_prefix = spec.document_routes[sub]
                ok, meta_payload, file_bytes, content_type = self._read_multipart()
                if not ok:
                    self._json(400, _wrap(spec, {"errorMessage": "multipart parse failed"}, ok=False))
                    return
                obj_id = f"{id_prefix}-{uuid.uuid4().hex[:10].upper()}"
                (_state_dir() / "uploads" / f"{obj_id}.bin").write_bytes(file_bytes)
                _append(spec.vendor, "documents", {
                    "id": obj_id,
                    "received_at": datetime.utcnow().isoformat() + "Z",
                    "metadata": meta_payload,
                    "size_bytes": len(file_bytes),
                    "content_type": content_type,
                })
                self._json(201, _wrap(spec, {"id": obj_id}))
                return

        self._json(404, {"error": "not_found", "path": self.path})

    # -- helpers ---------------------------------------------------------

    def _should_inject_failure(self) -> bool:
        try:
            rate = float(os.environ.get("LIMS_MOCK_FAIL_RATE", "0"))
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
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return False, {}, b"", ""
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


def _wrap(spec: VendorMockSpec, body: dict, ok: bool = True) -> dict:
    """Apply the vendor's preferred response envelope shape."""
    if spec.response_envelope == "nested":
        return {
            "responseStatus": "SUCCESS" if ok else "FAILURE",
            "result": body,
        }
    # flat
    base = {"responseStatus": "SUCCESS" if ok else "FAILURE"}
    base.update(body)
    return base


# ---------------------------------------------------------------------------
# Server runner — used by the management command
# ---------------------------------------------------------------------------

def serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), MockLimsHandler)
    _state_dir()  # ensure directory exists
    rate = os.environ.get("LIMS_MOCK_FAIL_RATE", "0")
    sys.stdout.write(
        f"LIMS MOCK server listening on http://{host}:{port}  "
        f"(fail_rate={rate}, state_dir={_state_dir()})\n"
        f"Registered vendors: "
        f"{', '.join(s.vendor for s in registered_vendors()) or '<none>'}\n"
    )
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nStopping LIMS mock server.\n")
        server.shutdown()
