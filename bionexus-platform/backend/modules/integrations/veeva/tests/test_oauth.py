"""Tests for the Veeva OAuth2 Authorization Code flow.

Mix of unit tests (mocked ``requests.post``) and LiveServerTestCase
tests (real HTTP roundtrips against the in-process mock OAuth Django
routes).
"""

from __future__ import annotations

import os
from datetime import timedelta
from unittest import mock

from django.test import LiveServerTestCase, TestCase, override_settings
from django.utils import timezone

from modules.integrations.veeva import mock_oauth, oauth
from modules.integrations.veeva.models import VeevaOAuthToken


@override_settings(SECRET_KEY="test-secret-veeva-oauth")
class EncryptionTest(TestCase):
    def test_round_trip(self) -> None:
        cipher = oauth.encrypt("MyP@ss!")
        self.assertNotEqual(cipher, "MyP@ss!")
        self.assertEqual(oauth.decrypt(cipher), "MyP@ss!")

    def test_empty_passthrough(self) -> None:
        self.assertEqual(oauth.encrypt(""), "")
        self.assertEqual(oauth.decrypt(""), "")

    def test_tampered_ciphertext_raises(self) -> None:
        cipher = oauth.encrypt("real")
        tampered = cipher[:-2] + "AA"
        with self.assertRaises(oauth.VeevaOAuthError):
            oauth.decrypt(tampered)

    def test_secret_key_rotation_breaks_old_ciphertext(self) -> None:
        cipher = oauth.encrypt("hello")
        with override_settings(SECRET_KEY="OTHER-key"):
            with self.assertRaises(oauth.VeevaOAuthError):
                oauth.decrypt(cipher)


@override_settings(SECRET_KEY="test-secret-veeva-oauth-state")
class StateFreshnessTest(TestCase):
    def test_state_match_accepted_when_fresh(self) -> None:
        state = oauth.mint_state_token()
        record = oauth._token_record()
        self.assertTrue(oauth._state_is_fresh(record, state))

    def test_state_mismatch_rejected(self) -> None:
        oauth.mint_state_token()
        record = oauth._token_record()
        self.assertFalse(oauth._state_is_fresh(record, "WRONG"))

    def test_state_expires_after_ttl(self) -> None:
        state = oauth.mint_state_token()
        record = oauth._token_record()
        record.oauth_state_created_at = timezone.now() - timedelta(minutes=15)
        record.save()
        self.assertFalse(oauth._state_is_fresh(record, state))


@override_settings(SECRET_KEY="test-secret-veeva-token-fresh")
class TokenFreshnessTest(TestCase):
    def _set_token(self, *, expires_at=None, token="at"):
        record = oauth._token_record()
        record.access_token_enc = oauth.encrypt(token) if token else ""
        record.token_expires_at = expires_at
        record.save()
        return record

    def test_no_token_is_stale(self) -> None:
        record = self._set_token(token=None)
        self.assertFalse(oauth._token_is_fresh(record))

    def test_expired_is_stale(self) -> None:
        record = self._set_token(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertFalse(oauth._token_is_fresh(record))

    def test_fresh_when_far_from_expiry(self) -> None:
        record = self._set_token(expires_at=timezone.now() + timedelta(minutes=30))
        self.assertTrue(oauth._token_is_fresh(record))

    def test_near_expiry_is_stale(self) -> None:
        record = self._set_token(expires_at=timezone.now() + timedelta(minutes=2))
        self.assertFalse(oauth._token_is_fresh(record))


@override_settings(SECRET_KEY="test-secret-veeva-exchange")
class CodeExchangeTest(TestCase):
    def setUp(self) -> None:
        self.env = {
            "VEEVA_OAUTH_CLIENT_ID": "lbn-client",
            "VEEVA_OAUTH_CLIENT_SECRET": "lbn-secret",
            "VEEVA_OAUTH_REDIRECT_URI": "http://localhost:3000/cb",
            "VEEVA_AUTH_FLOW": "oauth2",
        }

    def test_exchange_success_persists_tokens(self) -> None:
        fake = mock.Mock(status_code=200)
        fake.json.return_value = {
            "access_token": "AT-abc",
            "refresh_token": "RT-xyz",
            "expires_in": 3600,
        }
        with override_settings(VEEVA_BASE_URL="https://example.veevavault.com"):
            with mock.patch.dict(os.environ, self.env, clear=False):
                state = oauth.mint_state_token()
                with mock.patch(
                    "modules.integrations.veeva.oauth.requests.post",
                    return_value=fake,
                ):
                    at, rt = oauth.exchange_code_for_tokens("code-abc", state)
        self.assertEqual(at, "AT-abc")
        self.assertEqual(rt, "RT-xyz")
        record = oauth._token_record()
        self.assertEqual(oauth.decrypt(record.access_token_enc), "AT-abc")
        self.assertEqual(oauth.decrypt(record.refresh_token_enc), "RT-xyz")
        # State is single-use ; cleared
        self.assertEqual(record.oauth_state, "")

    def test_exchange_bad_state_raises(self) -> None:
        with mock.patch.dict(os.environ, self.env, clear=False):
            oauth.mint_state_token()
            with self.assertRaises(oauth.VeevaOAuthError):
                oauth.exchange_code_for_tokens("code", "WRONG-state")

    def test_exchange_token_endpoint_failure_raises(self) -> None:
        fake = mock.Mock(status_code=400, text="bad")
        with override_settings(VEEVA_BASE_URL="https://example.veevavault.com"):
            with mock.patch.dict(os.environ, self.env, clear=False):
                state = oauth.mint_state_token()
                with mock.patch(
                    "modules.integrations.veeva.oauth.requests.post",
                    return_value=fake,
                ):
                    with self.assertRaises(oauth.VeevaOAuthError):
                        oauth.exchange_code_for_tokens("code", state)

    def test_build_authorize_url_missing_config_raises(self) -> None:
        # No env vars set + no VEEVA_BASE_URL
        with override_settings(VEEVA_BASE_URL=""):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(oauth.VeevaOAuthError):
                    oauth.build_authorize_url()


@override_settings(
    SECRET_KEY="test-secret-veeva-e2e",
    DEBUG=True,  # enable Django mock OAuth routes
)
class OAuthEndToEndTest(LiveServerTestCase):
    """Real HTTP round-trips against the in-process mock OAuth Django routes."""

    def setUp(self) -> None:
        mock_oauth.reset_oauth_state()
        # Point env at the live mock running in this Django server
        self.env_patcher = mock.patch.dict(os.environ, {
            "VEEVA_AUTH_FLOW": "oauth2",
            "VEEVA_OAUTH_CLIENT_ID": "lbn-test-client",
            "VEEVA_OAUTH_CLIENT_SECRET": "lbn-test-secret",
            "VEEVA_OAUTH_REDIRECT_URI": (
                f"{self.live_server_url}/integrations/veeva/callback"
            ),
        }, clear=False)
        self.env_patcher.start()
        self.settings_override = override_settings(
            VEEVA_BASE_URL=f"{self.live_server_url}/mock-veeva",
        )
        self.settings_override.enable()

    def tearDown(self) -> None:
        self.settings_override.disable()
        self.env_patcher.stop()
        mock_oauth.reset_oauth_state()

    def _complete_dance(self) -> None:
        """Walk through authorize -> code -> token-exchange against the mock."""
        response = self.client.get("/api/integrations/veeva/oauth/authorize-url/")
        self.assertEqual(response.status_code, 200, response.content)
        authorize_url = response.data["authorize_url"]

        # Hit the mock authorize endpoint manually
        import requests as http
        from urllib.parse import parse_qs, urlparse

        ar = http.get(authorize_url, allow_redirects=False)
        self.assertIn(ar.status_code, (301, 302))
        params = parse_qs(urlparse(ar.headers["Location"]).query)
        code = params["code"][0]
        state = params["state"][0]

        # POST callback through the Django test client
        cb = self.client.post(
            "/api/integrations/veeva/oauth/callback/",
            {"code": code, "state": state},
            format="json",
        )
        self.assertEqual(cb.status_code, 200, cb.content)

    def test_full_oauth_dance_persists_token(self) -> None:
        self._complete_dance()
        record = VeevaOAuthToken.objects.get(pk=1)
        self.assertTrue(record.access_token_enc)
        self.assertIsNotNone(record.token_expires_at)

    def test_oauth_status_reports_active_token_after_dance(self) -> None:
        self._complete_dance()
        response = self.client.get("/api/integrations/veeva/oauth/status/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["oauth2_enabled"])
        self.assertTrue(response.data["has_active_token"])

    def test_callback_with_wrong_state_rejected(self) -> None:
        oauth.mint_state_token()
        response = self.client.post(
            "/api/integrations/veeva/oauth/callback/",
            {"code": "garbage", "state": "WRONG"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_refresh_token_rotation(self) -> None:
        self._complete_dance()
        record = VeevaOAuthToken.objects.get(pk=1)
        old_at = record.access_token_enc
        # Force expiry so the next call refreshes
        record.token_expires_at = timezone.now() - timedelta(minutes=1)
        record.save()

        new_at = oauth.get_or_refresh_access_token()
        self.assertTrue(new_at.startswith("vault-at-"))
        record.refresh_from_db()
        self.assertNotEqual(record.access_token_enc, old_at)


@override_settings(DEBUG=True, SECRET_KEY="test-secret-veeva-disabled")
class OAuthDisabledTest(TestCase):
    """When VEEVA_AUTH_FLOW != oauth2 the endpoints stay closed."""

    def test_authorize_url_400_when_disabled(self) -> None:
        with mock.patch.dict(os.environ, {"VEEVA_AUTH_FLOW": "session_id"}, clear=False):
            response = self.client.get("/api/integrations/veeva/oauth/authorize-url/")
        self.assertEqual(response.status_code, 400)

    def test_callback_400_when_disabled(self) -> None:
        with mock.patch.dict(os.environ, {"VEEVA_AUTH_FLOW": "session_id"}, clear=False):
            response = self.client.post(
                "/api/integrations/veeva/oauth/callback/",
                {"code": "x", "state": "y"},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
