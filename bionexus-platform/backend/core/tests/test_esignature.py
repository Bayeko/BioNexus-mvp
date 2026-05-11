"""Tests for e-signature upgrade: signature_meaning + TOTP verification."""

import pyotp
import pytest
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    CertifiedReport,
    ExecutionLog,
    Tenant,
    User,
    Role,
)
from core.tests.fixtures import create_test_tenant, create_test_role, create_test_user


@pytest.mark.django_db
class TestVerifyTOTP(TestCase):
    """Tests for User.verify_totp() method."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.role = create_test_role()
        self.user = create_test_user(
            tenant=self.tenant, role=self.role,
            username="totp_user", email="totp@lab.local",
        )

    def test_generate_totp_secret_stores_secret(self):
        secret = self.user.generate_totp_secret()
        self.user.refresh_from_db()
        assert self.user.totp_secret == secret
        assert len(secret) == 32
        assert self.user.totp_enabled is False

    def test_verify_totp_valid_code(self):
        self.user.generate_totp_secret()
        totp = pyotp.TOTP(self.user.totp_secret)
        code = totp.now()
        assert self.user.verify_totp(code) is True

    def test_verify_totp_invalid_code(self):
        self.user.generate_totp_secret()
        assert self.user.verify_totp("000000") is False

    def test_verify_totp_no_secret(self):
        assert self.user.verify_totp("123456") is False

    def test_get_totp_uri_contains_issuer(self):
        self.user.generate_totp_secret()
        uri = self.user.get_totp_uri()
        assert "otpauth://totp/" in uri
        assert "BioNexus" in uri
        # Email may be URL-encoded in the URI
        from urllib.parse import quote
        assert quote(self.user.email, safe="") in uri or self.user.email in uri


@pytest.mark.django_db
class TestSignatureMeaningRequired(TestCase):
    """Tests for signature_meaning being required on /api/reports/{id}/sign/."""

    def setUp(self):
        self.tenant = create_test_tenant(
            name="Sig Lab", slug="sig-lab",
        )
        self.role = create_test_role()
        self.user = create_test_user(
            tenant=self.tenant, role=self.role,
            username="signer", email="signer@lab.local",
            password="securepass123",
        )
        # Create minimal protocol for ExecutionLog FK
        from modules.protocols.models import Protocol
        self.protocol = Protocol.objects.create(
            title="Test Protocol",
            description="Test protocol for signing",
        )
        self.execution_log = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=self.protocol,
            started_by=self.user,
            started_at=timezone.now(),
            status="completed",
        )
        self.report = CertifiedReport.objects.create(
            tenant=self.tenant,
            execution_log=self.execution_log,
            report_hash="a" * 64,
            state=CertifiedReport.PENDING,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sign_without_signature_meaning_returns_400(self):
        """Signing without signature_meaning must return 400."""
        response = self.client.post(
            f"/api/reports/{self.report.id}/sign/",
            {"password": "securepass123"},
            format="json",
        )
        assert response.status_code == 400
        assert "signature_meaning" in response.json()["error"]

    def test_sign_with_invalid_signature_meaning_returns_400(self):
        response = self.client.post(
            f"/api/reports/{self.report.id}/sign/",
            {
                "password": "securepass123",
                "signature_meaning": "invalid_value",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_sign_with_valid_signature_meaning_succeeds(self):
        response = self.client.post(
            f"/api/reports/{self.report.id}/sign/",
            {
                "password": "securepass123",
                "signature_meaning": "approval",
            },
            format="json",
        )
        assert response.status_code == 200
        self.report.refresh_from_db()
        assert self.report.state == CertifiedReport.CERTIFIED
        assert self.report.signature_meaning == "approval"

    def test_sign_with_totp_enabled_requires_otp(self):
        """When TOTP is enabled, otp_code is required."""
        self.user.generate_totp_secret()
        self.user.totp_enabled = True
        self.user.save(update_fields=["totp_enabled"])

        response = self.client.post(
            f"/api/reports/{self.report.id}/sign/",
            {
                "password": "securepass123",
                "signature_meaning": "review",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "otp_code" in response.json()["error"]

    def test_sign_with_valid_totp_succeeds(self):
        """Full signing flow with TOTP."""
        self.user.generate_totp_secret()
        self.user.totp_enabled = True
        self.user.save(update_fields=["totp_enabled"])

        totp = pyotp.TOTP(self.user.totp_secret)
        response = self.client.post(
            f"/api/reports/{self.report.id}/sign/",
            {
                "password": "securepass123",
                "signature_meaning": "verification",
                "otp_code": totp.now(),
            },
            format="json",
        )
        assert response.status_code == 200
        self.report.refresh_from_db()
        assert self.report.state == CertifiedReport.CERTIFIED
