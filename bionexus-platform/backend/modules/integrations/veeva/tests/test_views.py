"""Tests for the read-only Veeva views (status + push log listing)."""

from datetime import datetime, timezone

import pytest
from rest_framework.test import APIClient

from modules.integrations.veeva.models import IntegrationPushLog


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def some_log_rows(db):
    IntegrationPushLog.objects.create(
        vendor=IntegrationPushLog.VENDOR_VEEVA,
        target_object_type=IntegrationPushLog.TARGET_QUALITY_EVENT,
        source_measurement_id=1,
        payload_hash="a" * 64,
        status=IntegrationPushLog.STATUS_SUCCESS,
        target_object_id="VVQE-A",
        http_status=201,
        mode="mock",
    )
    IntegrationPushLog.objects.create(
        vendor=IntegrationPushLog.VENDOR_VEEVA,
        target_object_type=IntegrationPushLog.TARGET_QUALITY_EVENT,
        source_measurement_id=2,
        payload_hash="b" * 64,
        status=IntegrationPushLog.STATUS_FAILED,
        http_status=500,
        last_error="HTTP 500",
        mode="mock",
    )
    IntegrationPushLog.objects.create(
        vendor=IntegrationPushLog.VENDOR_EMPOWER,
        target_object_type=IntegrationPushLog.TARGET_GENERIC_RESULT,
        source_measurement_id=3,
        payload_hash="c" * 64,
        status=IntegrationPushLog.STATUS_SUCCESS,
        target_object_id="EMPRES-Z",
        http_status=201,
        mode="mock",
    )


@pytest.mark.django_db
class TestVeevaStatus:
    def test_disabled_default(self, api_client, settings):
        settings.VEEVA_MODE = "disabled"
        settings.VEEVA_INTEGRATION_ENABLED = False
        resp = api_client.get("/api/integrations/veeva/status/")
        assert resp.status_code == 200
        assert resp.data["mode"] == "disabled"
        assert resp.data["enabled"] is False
        assert resp.data["label"] == "DISABLED"

    def test_mock_mode_label(self, api_client, settings):
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_BASE_URL = "http://localhost:8001"
        resp = api_client.get("/api/integrations/veeva/status/")
        assert resp.status_code == 200
        assert resp.data["mode"] == "mock"
        assert "MOCK MODE" in resp.data["label"]
        assert resp.data["base_url"] == "http://localhost:8001"

    def test_prod_redacts_url(self, api_client, settings):
        settings.VEEVA_MODE = "prod"
        settings.VEEVA_INTEGRATION_ENABLED = True
        settings.VEEVA_BASE_URL = "https://prod.veevavault.com"
        resp = api_client.get("/api/integrations/veeva/status/")
        assert resp.status_code == 200
        assert resp.data["base_url"] == "<redacted>"

    def test_counts_reflect_veeva_rows_by_default(self, api_client, settings, some_log_rows):
        settings.VEEVA_MODE = "mock"
        settings.VEEVA_INTEGRATION_ENABLED = True
        resp = api_client.get("/api/integrations/veeva/status/")
        counts = resp.data["counts"]
        # Default = veeva, so the Empower row is not counted.
        assert counts["total"] == 2
        assert counts["success"] == 1
        assert counts["failed"] == 1

    def test_vendor_filter_returns_only_that_vendor(
        self, api_client, settings, some_log_rows
    ):
        settings.EMPOWER_MODE = "mock"
        settings.EMPOWER_INTEGRATION_ENABLED = True
        resp = api_client.get("/api/integrations/veeva/status/?vendor=empower")
        assert resp.data["vendor"] == "empower"
        assert resp.data["mode"] == "mock"
        # Only 1 Empower row exists in the fixture.
        assert resp.data["counts"]["total"] == 1
        assert resp.data["counts"]["success"] == 1


@pytest.mark.django_db
class TestVeevaPushLogList:
    def test_list_returns_all_vendors_by_default(self, api_client, some_log_rows):
        resp = api_client.get("/api/integrations/veeva/log/")
        assert resp.status_code == 200
        results = (
            resp.data["results"] if isinstance(resp.data, dict) else resp.data
        )
        # Fixture: 2 Veeva rows + 1 Empower row.
        assert len(results) == 3

    def test_filter_by_vendor(self, api_client, some_log_rows):
        resp = api_client.get("/api/integrations/veeva/log/?vendor=empower")
        results = (
            resp.data["results"] if isinstance(resp.data, dict) else resp.data
        )
        assert len(results) == 1
        assert results[0]["target_object_id"] == "EMPRES-Z"

    def test_retrieve_single_row(self, api_client, some_log_rows):
        row = IntegrationPushLog.objects.first()
        resp = api_client.get(f"/api/integrations/veeva/log/{row.id}/")
        assert resp.status_code == 200
        assert resp.data["id"] == row.id
        assert resp.data["payload_hash"] == row.payload_hash

    def test_empty_list_when_no_pushes(self, api_client, db):
        resp = api_client.get("/api/integrations/veeva/log/")
        assert resp.status_code == 200
        results = (
            resp.data["results"] if isinstance(resp.data, dict) else resp.data
        )
        assert results == []
