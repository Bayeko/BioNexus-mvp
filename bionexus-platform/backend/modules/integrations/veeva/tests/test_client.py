"""Tests for the Veeva client layer.

Strategy:
  - No real network. We monkeypatch ``requests.request`` to capture
    outbound calls and inject responses, which lets us pin headers,
    payload shape, signing, error handling, and the factory's mode
    selection without standing up a real server.
"""

from unittest.mock import MagicMock, patch

import pytest

# HTTP shared code now lives in base/, so patches target base.client.requests.
from modules.integrations.base import client as client_mod
from modules.integrations.veeva.client import (
    DisabledVeevaClient,
    HttpVeevaClient,
    MockVeevaClient,
    ProdVeevaClient,
    SandboxVeevaClient,
    build_client_from_settings,
)
from modules.integrations.base.client import PushResult


SECRET = "secret-min-32-bytes-aaaaaaaaaaaaaaa"
PAYLOAD = {"parameter__v": "pH", "value__v": "7.42", "unit__v": "pH"}


# ---------------------------------------------------------------------------
# DisabledVeevaClient
# ---------------------------------------------------------------------------

class TestDisabledClient:
    def test_quality_event_no_op(self) -> None:
        result = DisabledVeevaClient().push_quality_event(PAYLOAD)
        assert result.ok is False
        assert result.http_status is None
        assert "disabled" in result.error.lower()

    def test_document_no_op(self) -> None:
        result = DisabledVeevaClient().push_document(PAYLOAD, b"pdf")
        assert result.ok is False
        assert "disabled" in result.error.lower()

    def test_falsy(self) -> None:
        result = DisabledVeevaClient().push_quality_event(PAYLOAD)
        assert not bool(result)


# ---------------------------------------------------------------------------
# MockVeevaClient (HTTP path)
# ---------------------------------------------------------------------------

def _make_response(status: int = 200, json_body=None, text: str = ""):
    resp = MagicMock()
    resp.ok = 200 <= status < 300
    resp.status_code = status
    if json_body is not None:
        resp.json.return_value = json_body
        resp.text = '{"ok": true}'  # not used but realistic
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = text
    return resp


class TestMockClientHappyPath:
    def test_push_quality_event_success(self) -> None:
        client = MockVeevaClient(
            base_url="http://localhost:8001",
            shared_secret=SECRET,
        )
        fake_resp = _make_response(
            status=201,
            json_body={"id": "VVQE-001234", "responseStatus": "SUCCESS"},
        )
        with patch.object(client_mod.requests, "request", return_value=fake_resp) as req:
            result = client.push_quality_event(PAYLOAD)

        assert result.ok is True
        assert result.http_status == 201
        assert result.vault_id == "VVQE-001234"
        # Verify URL + method + signature header
        call = req.call_args
        method, url = call.args
        assert method == "POST"
        assert url == "http://localhost:8001/api/v23.1/vobjects/quality_event__v"
        headers = call.kwargs["headers"]
        assert "X-BioNexus-Signature" in headers
        assert headers["X-BioNexus-Signature"].startswith("sha256=")
        assert call.kwargs["json"] == PAYLOAD

    def test_push_document_multipart(self) -> None:
        client = MockVeevaClient(
            base_url="http://localhost:8001",
            shared_secret=SECRET,
        )
        fake_resp = _make_response(
            status=201,
            json_body={"id": "VVDOC-005678", "responseStatus": "SUCCESS"},
        )
        with patch.object(client_mod.requests, "request", return_value=fake_resp) as req:
            result = client.push_document(PAYLOAD, b"%PDF-1.4 ...")

        assert result.ok is True
        assert result.vault_id == "VVDOC-005678"
        # Verify multipart files were attached
        files = req.call_args.kwargs["files"]
        assert "metadata" in files
        assert "file" in files
        assert files["file"][2] == "application/pdf"
        # Multipart leaves Content-Type to requests, so we must NOT set it
        headers = req.call_args.kwargs["headers"]
        assert "Content-Type" not in headers

    def test_latency_recorded(self) -> None:
        client = MockVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=200, json_body={"id": "X"})
        with patch.object(client_mod.requests, "request", return_value=fake_resp):
            result = client.push_quality_event(PAYLOAD)
        assert result.latency_ms >= 0


class TestMockClientFailureModes:
    def test_http_500_marks_failure(self) -> None:
        client = MockVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=500, text="boom")
        with patch.object(client_mod.requests, "request", return_value=fake_resp):
            result = client.push_quality_event(PAYLOAD)
        assert result.ok is False
        assert result.http_status == 500
        assert "500" in result.error
        assert "boom" in result.response_body_excerpt

    def test_http_400_marks_failure(self) -> None:
        client = MockVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=400, text="bad field")
        with patch.object(client_mod.requests, "request", return_value=fake_resp):
            result = client.push_quality_event(PAYLOAD)
        assert result.ok is False
        assert result.http_status == 400

    def test_transport_exception_caught(self) -> None:
        client = MockVeevaClient(base_url="http://x", shared_secret=SECRET)
        with patch.object(
            client_mod.requests,
            "request",
            side_effect=ConnectionError("refused"),
        ):
            result = client.push_quality_event(PAYLOAD)
        assert result.ok is False
        assert result.http_status is None
        assert "transport" in result.error.lower()

    def test_unparseable_response_still_returns_ok_on_2xx(self) -> None:
        """If Vault returns 2xx but the body isn't JSON, we still mark ok."""
        client = MockVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=200, text="not json")
        with patch.object(client_mod.requests, "request", return_value=fake_resp):
            result = client.push_quality_event(PAYLOAD)
        assert result.ok is True
        assert result.vault_id == ""


class TestSandboxClientAuth:
    def test_sandbox_includes_bearer_when_token_set(self, monkeypatch) -> None:
        monkeypatch.setenv("VEEVA_SESSION_TOKEN", "tok-abc")
        client = SandboxVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=200, json_body={"id": "X"})
        with patch.object(client_mod.requests, "request", return_value=fake_resp) as req:
            client.push_quality_event(PAYLOAD)
        headers = req.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tok-abc"

    def test_sandbox_no_bearer_when_token_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("VEEVA_SESSION_TOKEN", raising=False)
        client = SandboxVeevaClient(base_url="http://x", shared_secret=SECRET)
        fake_resp = _make_response(status=200, json_body={"id": "X"})
        with patch.object(client_mod.requests, "request", return_value=fake_resp) as req:
            client.push_quality_event(PAYLOAD)
        headers = req.call_args.kwargs["headers"]
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# Factory: build_client_from_settings
# ---------------------------------------------------------------------------

class TestBuildClientFromSettings:
    def test_disabled_default(self, settings) -> None:
        settings.VEEVA_MODE = "disabled"
        client = build_client_from_settings()
        assert isinstance(client, DisabledVeevaClient)

    def test_mock_builds_mock_client(self, settings) -> None:
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = "http://localhost:8001"
        settings.VEEVA_SHARED_SECRET = SECRET
        client = build_client_from_settings()
        assert isinstance(client, MockVeevaClient)

    def test_sandbox_builds_sandbox_client(self, settings) -> None:
        settings.VEEVA_MODE = "sandbox"
        settings.VEEVA_BASE_URL = "https://sandbox.veevavault.com"
        settings.VEEVA_SHARED_SECRET = SECRET
        client = build_client_from_settings()
        assert isinstance(client, SandboxVeevaClient)

    def test_prod_requires_confirmation(self, settings, monkeypatch) -> None:
        settings.VEEVA_MODE = "prod"
        settings.VEEVA_BASE_URL = "https://prod.veevavault.com"
        settings.VEEVA_SHARED_SECRET = SECRET
        monkeypatch.delenv("VEEVA_PROD_CONFIRMED", raising=False)
        client = build_client_from_settings()
        # Without confirmation, falls back to disabled — anti-accident guard.
        assert isinstance(client, DisabledVeevaClient)

    def test_prod_allowed_with_confirmation(
        self, settings, monkeypatch
    ) -> None:
        settings.VEEVA_MODE = "prod"
        settings.VEEVA_BASE_URL = "https://prod.veevavault.com"
        settings.VEEVA_SHARED_SECRET = SECRET
        monkeypatch.setenv("VEEVA_PROD_CONFIRMED", "true")
        client = build_client_from_settings()
        assert isinstance(client, ProdVeevaClient)

    def test_missing_base_url_falls_back_to_disabled(self, settings) -> None:
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = ""
        settings.VEEVA_SHARED_SECRET = SECRET
        client = build_client_from_settings()
        assert isinstance(client, DisabledVeevaClient)

    def test_missing_secret_falls_back_to_disabled(self, settings) -> None:
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_BASE_URL = "http://x"
        settings.VEEVA_SHARED_SECRET = ""
        client = build_client_from_settings()
        assert isinstance(client, DisabledVeevaClient)

    def test_unknown_mode_falls_back_to_disabled(self, settings) -> None:
        settings.VEEVA_MODE = "potato"
        settings.VEEVA_BASE_URL = "http://x"
        settings.VEEVA_SHARED_SECRET = SECRET
        client = build_client_from_settings()
        assert isinstance(client, DisabledVeevaClient)
