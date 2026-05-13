"""Tests for the pluggable encryption module.

Covers :
- Default ``secret_key`` provider round-trip + key rotation invalidates
- ``env_key`` provider round-trip + missing key error
- ``gcp_kms`` provider raises clear error when google-cloud-kms is
  not installed
- Factory dispatch on ENCRYPTION_PROVIDER setting / env var
- Prefix-based decrypt routing (lets a deployment decrypt old-format
  rows after switching providers)
- Tampering raises EncryptionError
"""

from __future__ import annotations

import os
from unittest import mock

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from core.encryption import (
    EncryptionError,
    EnvKeyProvider,
    GcpKmsKeyProvider,
    SecretKeyDerivedKeyProvider,
    decrypt,
    encrypt,
    get_key_provider,
)


class SecretKeyProviderTest(TestCase):
    @override_settings(SECRET_KEY="test-secret-A")
    def test_round_trip(self) -> None:
        provider = SecretKeyDerivedKeyProvider()
        cipher = provider.encrypt("hello")
        self.assertTrue(cipher.startswith("sk1$"))
        self.assertEqual(provider.decrypt(cipher), "hello")

    @override_settings(SECRET_KEY="test-secret-B")
    def test_empty_passthrough(self) -> None:
        provider = SecretKeyDerivedKeyProvider()
        self.assertEqual(provider.encrypt(""), "")
        self.assertEqual(provider.decrypt(""), "")

    def test_secret_key_rotation_invalidates_ciphertext(self) -> None:
        with override_settings(SECRET_KEY="original"):
            cipher = SecretKeyDerivedKeyProvider().encrypt("hello")
        with override_settings(SECRET_KEY="rotated"):
            with self.assertRaises(EncryptionError):
                SecretKeyDerivedKeyProvider().decrypt(cipher)

    @override_settings(SECRET_KEY="tamper-test")
    def test_tampering_raises(self) -> None:
        provider = SecretKeyDerivedKeyProvider()
        cipher = provider.encrypt("hello")
        tampered = cipher[:-2] + "AA"
        with self.assertRaises(EncryptionError):
            provider.decrypt(tampered)


class EnvKeyProviderTest(TestCase):
    def setUp(self) -> None:
        self.key = Fernet.generate_key().decode("utf-8")

    def test_round_trip(self) -> None:
        with mock.patch.dict(os.environ, {"ENCRYPTION_KEY": self.key}):
            provider = EnvKeyProvider()
            cipher = provider.encrypt("hello")
            self.assertTrue(cipher.startswith("ek1$"))
            self.assertEqual(provider.decrypt(cipher), "hello")

    def test_missing_key_raises(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EncryptionError):
                EnvKeyProvider().encrypt("hello")

    def test_malformed_key_raises(self) -> None:
        with mock.patch.dict(os.environ, {"ENCRYPTION_KEY": "not-a-valid-key"}):
            with self.assertRaises(EncryptionError):
                EnvKeyProvider().encrypt("hello")

    def test_empty_passthrough(self) -> None:
        with mock.patch.dict(os.environ, {"ENCRYPTION_KEY": self.key}):
            provider = EnvKeyProvider()
            self.assertEqual(provider.encrypt(""), "")
            self.assertEqual(provider.decrypt(""), "")


class GcpKmsProviderStubTest(TestCase):
    def test_raises_when_package_missing(self) -> None:
        """The stub should fail loud when google-cloud-kms is not installed."""
        provider = GcpKmsKeyProvider()
        # Force the import to fail by hiding google.cloud.kms_v1
        with mock.patch.dict(
            "sys.modules", {"google.cloud.kms_v1": None},
        ):
            with self.assertRaises(EncryptionError) as cm:
                provider.encrypt("hello")
            self.assertIn("google-cloud-kms", str(cm.exception))

    def test_raises_when_env_missing(self) -> None:
        """When package is missing OR env vars are missing, we raise."""
        provider = GcpKmsKeyProvider()
        # Even before checking env, the package import should fail in CI.
        with self.assertRaises(EncryptionError):
            provider.encrypt("anything")


class FactoryDispatchTest(TestCase):
    @override_settings(ENCRYPTION_PROVIDER="secret_key")
    def test_default_is_secret_key(self) -> None:
        provider = get_key_provider()
        self.assertIsInstance(provider, SecretKeyDerivedKeyProvider)

    @override_settings(ENCRYPTION_PROVIDER="env_key")
    def test_dispatch_env_key(self) -> None:
        provider = get_key_provider()
        self.assertIsInstance(provider, EnvKeyProvider)

    @override_settings(ENCRYPTION_PROVIDER="gcp_kms")
    def test_dispatch_gcp_kms(self) -> None:
        provider = get_key_provider()
        self.assertIsInstance(provider, GcpKmsKeyProvider)

    @override_settings(ENCRYPTION_PROVIDER="unknown")
    def test_unknown_provider_raises(self) -> None:
        with self.assertRaises(EncryptionError):
            get_key_provider()


class PrefixRoutingTest(TestCase):
    """decrypt() at module level routes by ciphertext prefix.

    This lets a deployment mid-migration decrypt rows produced by a
    previous provider without breaking. The currently-configured
    provider only matters when no prefix is found OR for new encrypts.
    """

    @override_settings(SECRET_KEY="prefix-route-test", ENCRYPTION_PROVIDER="env_key")
    def test_decrypt_routes_old_secret_key_ciphertext(self) -> None:
        # Produce ciphertext with the secret_key provider explicitly
        old_cipher = SecretKeyDerivedKeyProvider().encrypt("legacy-secret")

        # Now the deployment is configured for env_key, but it can
        # still decrypt the prefix-tagged old-format row.
        key = Fernet.generate_key().decode("utf-8")
        with mock.patch.dict(os.environ, {"ENCRYPTION_KEY": key}):
            self.assertEqual(decrypt(old_cipher), "legacy-secret")

    @override_settings(SECRET_KEY="no-prefix-test", ENCRYPTION_PROVIDER="secret_key")
    def test_legacy_no_prefix_ciphertext_falls_back(self) -> None:
        """A pre-prefix ciphertext (no ``sk1$`` tag) still decrypts.

        Useful when migrating an existing database that has stored
        Fernet tokens from before the prefix was introduced.
        """
        # Build an old-style ciphertext without the prefix
        provider = SecretKeyDerivedKeyProvider()
        prefixed = provider.encrypt("legacy")
        # Strip the prefix by hand to simulate old data
        legacy = prefixed.split("$", 1)[1]
        self.assertEqual(decrypt(legacy), "legacy")


class ModuleLevelHelpersTest(TestCase):
    """encrypt() / decrypt() module functions use the configured provider."""

    @override_settings(SECRET_KEY="module-level-test", ENCRYPTION_PROVIDER="secret_key")
    def test_module_round_trip(self) -> None:
        cipher = encrypt("plaintext")
        self.assertEqual(decrypt(cipher), "plaintext")

    @override_settings(SECRET_KEY="empty-test", ENCRYPTION_PROVIDER="secret_key")
    def test_empty_input(self) -> None:
        self.assertEqual(encrypt(""), "")
        self.assertEqual(decrypt(""), "")
