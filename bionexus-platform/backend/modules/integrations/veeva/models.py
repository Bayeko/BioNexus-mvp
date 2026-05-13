"""IntegrationPushLog — append-only audit of every Veeva Vault push attempt.

Per LBN-INT-VEEVA-001 §3, the integration must record every outbound push
(success or failure) so that:
  - QA can reconstruct what was sent to Vault at any point in time
  - The retry / DLQ subsystem has authoritative state
  - The SHA-256 audit chain (core.AuditLog) is informed of integration events

This model is append-only: once a row is written it is never mutated except
to record retry attempts on the same row (attempts counter + last_error).
Successful pushes never have their `target_object_id` cleared.
"""

from django.db import models


class IntegrationPushLog(models.Model):
    """Audit record for a single push attempt to Veeva Vault.

    State machine:
        pending → in_flight → success
                            → failed → (retry) → in_flight → ...
                                              → dead_letter (max retries exceeded)
    """

    STATUS_PENDING = "pending"
    STATUS_IN_FLIGHT = "in_flight"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_DEAD_LETTER = "dead_letter"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_FLIGHT, "In flight"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed (will retry)"),
        (STATUS_DEAD_LETTER, "Dead letter (max retries exceeded)"),
    ]

    TARGET_QUALITY_EVENT = "quality_event__v"
    TARGET_DOCUMENT = "document__v"
    TARGET_AUDIT_ATTACHMENT = "audit_attachment__v"
    # Generic targets used by non-Veeva vendors. The string value is the
    # vendor-specific object name — Empower "Result", LabWare "Sample",
    # STARLIMS "TestResult", Benchling "ResultRow", etc.
    TARGET_GENERIC_RESULT = "result"
    TARGET_GENERIC_SAMPLE = "sample"
    TARGET_GENERIC_ENTRY = "entry"
    TARGET_CHOICES = [
        (TARGET_QUALITY_EVENT, "quality_event__v"),
        (TARGET_DOCUMENT, "document__v"),
        (TARGET_AUDIT_ATTACHMENT, "audit_attachment__v"),
        (TARGET_GENERIC_RESULT, "result"),
        (TARGET_GENERIC_SAMPLE, "sample"),
        (TARGET_GENERIC_ENTRY, "entry"),
    ]

    VENDOR_VEEVA = "veeva"
    VENDOR_EMPOWER = "empower"
    VENDOR_LABWARE = "labware"
    VENDOR_STARLIMS = "starlims"
    VENDOR_BENCHLING = "benchling"
    VENDOR_CHOICES = [
        (VENDOR_VEEVA, "Veeva Vault QMS"),
        (VENDOR_EMPOWER, "Waters Empower"),
        (VENDOR_LABWARE, "LabWare LIMS"),
        (VENDOR_STARLIMS, "STARLIMS"),
        (VENDOR_BENCHLING, "Benchling ELN"),
    ]

    MODE_DISABLED = "disabled"
    MODE_MOCK = "mock"
    MODE_SANDBOX = "sandbox"
    MODE_PROD = "prod"
    MODE_CHOICES = [
        (MODE_DISABLED, "Disabled"),
        (MODE_MOCK, "Mock"),
        (MODE_SANDBOX, "Sandbox"),
        (MODE_PROD, "Production"),
    ]

    # Which LIMS / QMS / ELN this push targeted. Lets one table serve
    # every vendor without colliding on object ID namespaces.
    vendor = models.CharField(
        max_length=32,
        choices=VENDOR_CHOICES,
        default=VENDOR_VEEVA,
        db_index=True,
        help_text="Which downstream system the push targeted.",
    )

    # What was pushed
    target_object_type = models.CharField(
        max_length=64,
        choices=TARGET_CHOICES,
        help_text="Object type the payload was destined for (vendor-specific).",
    )
    source_measurement_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "ID of the BioNexus Measurement that triggered this push, when "
            "applicable. Null for non-measurement pushes (e.g. standalone "
            "document attachments)."
        ),
    )
    source_report_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the BioNexus CertifiedReport, for document pushes.",
    )

    # Idempotency: a SHA-256 over the canonical payload. Used so that a
    # retry doesn't double-push if Vault already accepted the previous try.
    payload_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hex of the canonical payload sent to Vault.",
    )

    # Where it landed
    target_object_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Vault-assigned object ID returned on success (e.g. VVQE-001234). "
            "Empty string until a successful response is recorded."
        ),
    )

    # HTTP / transport state
    http_status = models.IntegerField(
        null=True,
        blank=True,
        help_text="HTTP status code from Vault on the most recent attempt.",
    )
    response_body_excerpt = models.TextField(
        blank=True,
        default="",
        help_text="First 2 KB of the Vault response body, for debugging.",
    )
    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Most recent error message (transport, parse, or Vault).",
    )

    # Retry accounting
    attempts = models.IntegerField(
        default=0,
        help_text="Number of push attempts made so far.",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # Context
    mode = models.CharField(
        max_length=16,
        choices=MODE_CHOICES,
        default=MODE_DISABLED,
        help_text="VEEVA_MODE active at the moment of the push attempt.",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    succeeded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "integrations_veeva_push_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="iv_pushlog_status_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"VeevaPushLog#{self.pk} "
            f"target={self.target_object_type} "
            f"status={self.status} "
            f"vault_id={self.target_object_id or '-'}"
        )


# ---------------------------------------------------------------------------
# OAuth2 token cache (singleton)
# ---------------------------------------------------------------------------

class VeevaOAuthToken(models.Model):
    """Singleton row that caches the active Vault OAuth2 tokens.

    v1 supports one OAuth identity per Labionexus deployment, so the
    table is operated as a singleton on pk=1. The columns store the
    encrypted access + refresh tokens (Fernet, key derived from
    SECRET_KEY) plus the active CSRF state token mid-flow.

    Storing the tokens persistently — rather than in a cache — means
    a Django restart does not force the operator to re-authorize.
    State is short-lived (10 min TTL enforced in code) so even if a
    crash leaves it stale, the next flow simply mints a new one.
    """

    # --- Encrypted token credentials ---
    access_token_enc = models.TextField(
        blank=True,
        help_text="Fernet-encrypted OAuth2 access token. Refreshed automatically.",
    )
    refresh_token_enc = models.TextField(
        blank=True,
        help_text="Fernet-encrypted OAuth2 refresh token. Long-lived.",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the cached access token expires (UTC).",
    )

    # --- CSRF state for in-progress authorize flow ---
    oauth_state = models.CharField(
        max_length=128,
        blank=True,
        help_text=(
            "CSRF state token for the current authorize flow. "
            "Cleared once the callback succeeds, or after 10 min."
        ),
    )
    oauth_state_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the active state token was minted (10-min TTL).",
    )

    # --- Bookkeeping ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations_veeva_oauth_token"
        verbose_name = "Veeva OAuth2 token"
        verbose_name_plural = "Veeva OAuth2 tokens"

    def __str__(self) -> str:
        if self.access_token_enc and self.token_expires_at:
            return f"VeevaOAuthToken (expires {self.token_expires_at.isoformat()})"
        return "VeevaOAuthToken (uninitialised)"
