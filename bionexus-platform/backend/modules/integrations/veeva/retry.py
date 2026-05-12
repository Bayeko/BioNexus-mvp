"""Retry policy for Veeva Vault pushes (LBN-INT-VEEVA-001 §7).

Rules:
  - 5xx and transport errors: retry with exponential backoff + jitter.
  - 4xx (except 408 Request Timeout and 429 Too Many Requests): give up
    immediately. Client-side errors will not become success on retry.
  - Max attempts: 5 (configurable via VEEVA_MAX_RETRIES). After that the
    push lands in the dead-letter state on :class:`IntegrationPushLog`
    and waits for a human operator.

Backoff formula::

    delay_s = min(MAX_DELAY_S, BASE_DELAY_S * 2 ** (attempt - 1)) + jitter
    jitter  = random() * BASE_DELAY_S

The exponential cap prevents the delay from blowing up to hours, and
jitter prevents a "thundering herd" of retries hammering Vault after a
brief outage.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


BASE_DELAY_S = 1.0
MAX_DELAY_S = 300.0
DEFAULT_MAX_ATTEMPTS = 5

# 408 = Request Timeout (idempotent retry safe)
# 429 = Too Many Requests (Vault is telling us to back off)
# Everything else in 4xx is a client error that won't fix itself.
RETRYABLE_4XX = frozenset({408, 429})


@dataclass
class RetryDecision:
    """Outcome of evaluating whether to retry after a failure."""

    should_retry: bool
    delay_s: float
    reason: str

    def __bool__(self) -> bool:
        return self.should_retry


def is_retryable_status(http_status: int | None) -> bool:
    """Return True if the HTTP status warrants another attempt.

    None means "no response was received at all" (transport error,
    connection refused, DNS) — always retryable.
    """
    if http_status is None:
        return True
    if 500 <= http_status < 600:
        return True
    if http_status in RETRYABLE_4XX:
        return True
    return False


def backoff_delay(attempt: int, base: float = BASE_DELAY_S, cap: float = MAX_DELAY_S) -> float:
    """Return the next backoff delay in seconds for the given attempt number.

    ``attempt`` is 1-based — the first retry uses ``base`` seconds.
    """
    if attempt < 1:
        return 0.0
    raw = base * (2 ** (attempt - 1))
    capped = min(cap, raw)
    jitter = random.random() * base
    return capped + jitter


def decide(
    *,
    http_status: int | None,
    attempts: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> RetryDecision:
    """Decide whether the caller should retry after a failed push.

    ``attempts`` is the count of attempts *already made* including the
    one that just failed. ``max_attempts`` is the hard cap.
    """
    if attempts >= max_attempts:
        return RetryDecision(
            should_retry=False,
            delay_s=0.0,
            reason=f"max_attempts={max_attempts} exhausted",
        )

    if not is_retryable_status(http_status):
        return RetryDecision(
            should_retry=False,
            delay_s=0.0,
            reason=f"non-retryable status {http_status}",
        )

    delay = backoff_delay(attempt=attempts)
    return RetryDecision(
        should_retry=True,
        delay_s=delay,
        reason=(
            f"transport error, attempt {attempts}/{max_attempts}"
            if http_status is None
            else f"retryable status {http_status}, attempt {attempts}/{max_attempts}"
        ),
    )
