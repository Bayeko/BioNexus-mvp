"""Tests for the retry policy."""

import pytest

from modules.integrations.veeva.retry import (
    BASE_DELAY_S,
    DEFAULT_MAX_ATTEMPTS,
    MAX_DELAY_S,
    backoff_delay,
    decide,
    is_retryable_status,
)


class TestIsRetryableStatus:
    @pytest.mark.parametrize("status", [500, 502, 503, 504, 599])
    def test_5xx_retryable(self, status: int) -> None:
        assert is_retryable_status(status) is True

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
    def test_normal_4xx_not_retryable(self, status: int) -> None:
        assert is_retryable_status(status) is False

    def test_408_retryable(self) -> None:
        assert is_retryable_status(408) is True

    def test_429_retryable(self) -> None:
        assert is_retryable_status(429) is True

    def test_2xx_not_retryable(self) -> None:
        # Pure 2xx wouldn't even hit the retry path, but be defensive.
        assert is_retryable_status(200) is False
        assert is_retryable_status(201) is False

    def test_none_status_retryable(self) -> None:
        """Transport error / no response received → always retry."""
        assert is_retryable_status(None) is True


class TestBackoffDelay:
    def test_increases_exponentially(self) -> None:
        d1 = backoff_delay(1)
        d2 = backoff_delay(2)
        d3 = backoff_delay(3)
        # Floor of d_n = BASE * 2^(n-1) (jitter only adds, never subtracts).
        assert d1 >= BASE_DELAY_S
        assert d2 >= 2 * BASE_DELAY_S
        assert d3 >= 4 * BASE_DELAY_S

    def test_capped_at_max(self) -> None:
        # 2 ** 20 is well past MAX_DELAY_S — the cap must kick in.
        d = backoff_delay(20)
        assert d <= MAX_DELAY_S + BASE_DELAY_S  # cap + max jitter

    def test_zero_or_negative_attempt(self) -> None:
        assert backoff_delay(0) == 0.0
        assert backoff_delay(-1) == 0.0

    def test_jitter_varies(self) -> None:
        """100 draws of the same attempt should show >1 distinct value."""
        samples = {backoff_delay(3) for _ in range(100)}
        assert len(samples) > 1


class TestDecide:
    def test_5xx_first_attempt_retries(self) -> None:
        d = decide(http_status=500, attempts=1)
        assert d.should_retry is True
        assert d.delay_s > 0
        assert "500" in d.reason

    def test_4xx_does_not_retry(self) -> None:
        d = decide(http_status=400, attempts=1)
        assert d.should_retry is False
        assert "non-retryable" in d.reason

    def test_transport_error_retries(self) -> None:
        d = decide(http_status=None, attempts=1)
        assert d.should_retry is True
        assert "transport" in d.reason.lower()

    def test_max_attempts_caps(self) -> None:
        d = decide(http_status=500, attempts=DEFAULT_MAX_ATTEMPTS)
        assert d.should_retry is False
        assert "exhausted" in d.reason

    def test_max_attempts_configurable(self) -> None:
        d = decide(http_status=500, attempts=3, max_attempts=3)
        assert d.should_retry is False

    def test_429_retries(self) -> None:
        d = decide(http_status=429, attempts=1)
        assert d.should_retry is True

    def test_408_retries(self) -> None:
        d = decide(http_status=408, attempts=1)
        assert d.should_retry is True
