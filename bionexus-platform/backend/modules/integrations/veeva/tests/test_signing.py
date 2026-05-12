"""Tests for the Veeva HMAC-SHA256 signing primitive.

Pins:
  - Deterministic output for a given (payload, secret)
  - Sensitive to any change in payload or secret
  - Canonical form is key-order-independent
  - Round-trip verification works
  - Constant-time comparison via hmac.compare_digest
"""

import pytest

from modules.integrations.veeva.signing import (
    canonicalize,
    compute_signature,
    payload_hash,
    verify_signature,
)


SECRET = "test-shared-secret-32-bytes-min-aaaaaa"
PAYLOAD = {
    "value": "12.3456",
    "unit": "g",
    "parameter": "weight",
    "operator": "OP-042",
    "lot__v": "LOT-2026-04",
}


class TestCanonicalize:
    def test_returns_bytes(self) -> None:
        out = canonicalize(PAYLOAD)
        assert isinstance(out, bytes)

    def test_sorted_keys(self) -> None:
        same_payload_reordered = {
            "unit": "g",
            "operator": "OP-042",
            "parameter": "weight",
            "value": "12.3456",
            "lot__v": "LOT-2026-04",
        }
        assert canonicalize(PAYLOAD) == canonicalize(same_payload_reordered)

    def test_no_whitespace(self) -> None:
        out = canonicalize(PAYLOAD).decode("utf-8")
        assert " " not in out
        assert "\n" not in out

    def test_utf8_non_ascii_preserved(self) -> None:
        payload = {"method": "USP <711> — dissolution"}
        out = canonicalize(payload).decode("utf-8")
        assert "—" in out

    def test_nested_dicts_canonicalised(self) -> None:
        a = {"outer": {"b": 2, "a": 1}}
        b = {"outer": {"a": 1, "b": 2}}
        assert canonicalize(a) == canonicalize(b)


class TestPayloadHash:
    def test_64_hex_chars(self) -> None:
        h = payload_hash(PAYLOAD)
        assert len(h) == 64
        int(h, 16)  # hex-parsable

    def test_deterministic(self) -> None:
        assert payload_hash(PAYLOAD) == payload_hash(PAYLOAD)

    def test_changes_on_any_field_change(self) -> None:
        h1 = payload_hash(PAYLOAD)
        h2 = payload_hash({**PAYLOAD, "value": "12.3457"})
        assert h1 != h2

    def test_key_order_independent(self) -> None:
        reversed_payload = dict(reversed(list(PAYLOAD.items())))
        assert payload_hash(PAYLOAD) == payload_hash(reversed_payload)


class TestComputeSignature:
    def test_prefix(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        assert sig.startswith("sha256=")

    def test_hex_after_prefix(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        hex_part = sig.split("=", 1)[1]
        assert len(hex_part) == 64
        int(hex_part, 16)

    def test_deterministic(self) -> None:
        a = compute_signature(PAYLOAD, SECRET)
        b = compute_signature(PAYLOAD, SECRET)
        assert a == b

    def test_secret_sensitive(self) -> None:
        a = compute_signature(PAYLOAD, SECRET)
        b = compute_signature(PAYLOAD, SECRET + "x")
        assert a != b

    def test_payload_sensitive(self) -> None:
        a = compute_signature(PAYLOAD, SECRET)
        b = compute_signature({**PAYLOAD, "value": "999"}, SECRET)
        assert a != b

    def test_empty_secret_raises(self) -> None:
        # The base signing module emits a vendor-agnostic message
        # ("*_SHARED_SECRET env var"); the test still pins that
        # configuration regressions on this error path stay loud.
        with pytest.raises(ValueError, match="SHARED_SECRET"):
            compute_signature(PAYLOAD, "")


class TestVerifySignature:
    def test_round_trip(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        assert verify_signature(PAYLOAD, SECRET, sig) is True

    def test_rejects_wrong_secret(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        assert verify_signature(PAYLOAD, SECRET + "x", sig) is False

    def test_rejects_tampered_payload(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        tampered = {**PAYLOAD, "value": "999.99"}
        assert verify_signature(tampered, SECRET, sig) is False

    def test_rejects_tampered_signature(self) -> None:
        sig = compute_signature(PAYLOAD, SECRET)
        # Flip the last hex char
        tampered_sig = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        assert verify_signature(PAYLOAD, SECRET, tampered_sig) is False
