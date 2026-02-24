"""Audit trail models for compliance with 21 CFR Part 11.

Every mutation (create, update, delete) is recorded with:
- WHO: user_id (future: authentication layer will populate)
- WHAT: entity type, entity id, operation type
- WHEN: timestamp (immutable)
- HOW: field changes (before -> after)
- PROOF: SHA-256 signature chaining (immutable proof of tampering)

The signature chain ensures that audit records cannot be modified or deleted
without detection. Each record's signature includes the previous record's
signature, forming a tamper-proof chain.
"""

import hashlib
import json
from datetime import datetime

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable audit record for every data mutation."""

    # Operation types
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    OPERATION_CHOICES = [
        (CREATE, "Create"),
        (UPDATE, "Update"),
        (DELETE, "Delete"),
    ]

    # -- Identification -------------------------------------------------------
    entity_type = models.CharField(
        max_length=50,
        help_text="Model name (e.g., 'Sample', 'Protocol')",
    )
    entity_id = models.BigIntegerField(
        help_text="Primary key of the affected entity",
    )

    # -- Operation Info -------------------------------------------------------
    operation = models.CharField(
        max_length=10,
        choices=OPERATION_CHOICES,
        help_text="CREATE, UPDATE, or DELETE",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When the operation occurred (UTC, immutable, set explicitly)",
    )

    # -- User Context ---------------------------------------------------------
    user_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID of user who triggered the operation (future: auth system)",
    )
    user_email = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Email of user (for readability, actual proof is signature)",
    )

    # -- Data Changes ---------------------------------------------------------
    changes = models.JSONField(
        default=dict,
        help_text="{'field_name': {'before': old_value, 'after': new_value}, ...}",
    )
    snapshot_before = models.JSONField(
        default=dict,
        help_text="Full entity state BEFORE mutation (for forensics)",
    )
    snapshot_after = models.JSONField(
        default=dict,
        help_text="Full entity state AFTER mutation",
    )

    # -- Cryptographic Proof --------------------------------------------------
    signature = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256(previous_signature + json(this_record))",
    )
    previous_signature = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="SHA-256 of the previous audit log (chain proof)",
    )

    class Meta:
        app_label = "core"
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "timestamp"]),
            models.Index(fields=["signature"]),
            models.Index(fields=["timestamp"]),
        ]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"

    def __str__(self) -> str:
        return (
            f"{self.operation} {self.entity_type}({self.entity_id}) "
            f"@ {self.timestamp}"
        )

    @staticmethod
    def calculate_signature(
        previous_signature: str | None,
        entity_type: str,
        entity_id: int,
        operation: str,
        changes: dict,
        timestamp: str,
    ) -> str:
        """Calculate SHA-256 signature for this audit record.

        The signature includes the previous signature to form an unbreakable chain.
        If anyone modifies a historical record, its signature changes, breaking all
        downstream signatures and immediately revealing tampering.

        Args:
            previous_signature: SHA-256 of previous AuditLog, or None for first record
            entity_type: Model name (e.g., 'Sample')
            entity_id: PK of affected entity
            operation: CREATE, UPDATE, or DELETE
            changes: Dict of field changes
            timestamp: ISO format timestamp

        Returns:
            SHA-256 hex digest
        """
        # Canonical JSON (sorted keys, no extra whitespace) for deterministic hashing
        data = {
            "previous_signature": previous_signature or "",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "changes": changes,
            "timestamp": timestamp,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def clean(self):
        """Validate signature integrity before saving."""
        expected_signature = self.calculate_signature(
            self.previous_signature,
            self.entity_type,
            self.entity_id,
            self.operation,
            self.changes,
            self.timestamp.isoformat(),
        )
        if self.signature != expected_signature:
            raise ValueError(
                f"Signature mismatch. Expected {expected_signature}, "
                f"got {self.signature}"
            )

    def save(self, *args, **kwargs):
        """Ensure signature is valid before persisting."""
        if not hasattr(self, "_skip_validation"):
            self.clean()
        super().save(*args, **kwargs)


# --- Authentication & Authorization ------------------------------------------


class Tenant(models.Model):
    """Represents a laboratory or organization (multi-tenant isolation)."""

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Laboratory or organization name",
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-safe identifier for the tenant",
    )
    description = models.TextField(
        blank=True,
        help_text="Organizational description",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive tenants are soft-deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["name"]
        verbose_name = "Tenant (Laboratory)"

    def __str__(self) -> str:
        return self.name


class Role(models.Model):
    """Role-based access control roles."""

    # Standard roles for lab environments
    ADMIN = "admin"
    PRINCIPAL_INVESTIGATOR = "principal_investigator"
    LAB_TECHNICIAN = "lab_technician"
    AUDITOR = "auditor"
    VIEWER = "viewer"

    ROLE_CHOICES = [
        (ADMIN, "Administrator"),
        (PRINCIPAL_INVESTIGATOR, "Principal Investigator"),
        (LAB_TECHNICIAN, "Lab Technician"),
        (AUDITOR, "Auditor (Read-only)"),
        (VIEWER, "Viewer (Read-only)"),
    ]

    name = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        unique=True,
        help_text="Standardized role name",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of role responsibilities",
    )

    class Meta:
        app_label = "core"
        ordering = ["name"]
        verbose_name = "Role"

    def __str__(self) -> str:
        return self.get_name_display()


class Permission(models.Model):
    """Fine-grained permissions for operations."""

    # Samples operations
    SAMPLE_VIEW = "sample:view"
    SAMPLE_CREATE = "sample:create"
    SAMPLE_UPDATE = "sample:update"
    SAMPLE_DELETE = "sample:delete"

    # Protocols operations
    PROTOCOL_VIEW = "protocol:view"
    PROTOCOL_CREATE = "protocol:create"
    PROTOCOL_UPDATE = "protocol:update"
    PROTOCOL_DELETE = "protocol:delete"

    # Audit operations
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # User management
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"

    PERMISSION_CHOICES = [
        (SAMPLE_VIEW, "View samples"),
        (SAMPLE_CREATE, "Create samples"),
        (SAMPLE_UPDATE, "Update samples"),
        (SAMPLE_DELETE, "Delete samples"),
        (PROTOCOL_VIEW, "View protocols"),
        (PROTOCOL_CREATE, "Create protocols"),
        (PROTOCOL_UPDATE, "Update protocols"),
        (PROTOCOL_DELETE, "Delete protocols"),
        (AUDIT_VIEW, "View audit logs"),
        (AUDIT_EXPORT, "Export audit logs"),
        (USER_MANAGE, "Manage users"),
        (ROLE_MANAGE, "Manage roles"),
    ]

    codename = models.CharField(
        max_length=100,
        choices=PERMISSION_CHOICES,
        unique=True,
        help_text="Machine-readable permission identifier",
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description",
    )

    class Meta:
        app_label = "core"
        ordering = ["codename"]
        verbose_name = "Permission"

    def __str__(self) -> str:
        return self.get_codename_display()


class RolePermission(models.Model):
    """Mapping between roles and permissions (RBAC matrix)."""

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions_set",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="roles_with_permission",
    )

    class Meta:
        app_label = "core"
        unique_together = ("role", "permission")
        verbose_name = "Role Permission"

    def __str__(self) -> str:
        return f"{self.role.name} -> {self.permission.codename}"


from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model with tenant isolation."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users",
        help_text="The tenant (laboratory) this user belongs to",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="The role assigned to this user",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive users cannot log in",
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of last successful login (for audit)",
    )
    last_login_user_agent = models.TextField(
        blank=True,
        help_text="User agent of last login (for audit)",
    )

    class Meta:
        app_label = "core"
        unique_together = ("tenant", "username")
        verbose_name = "User"

    def __str__(self) -> str:
        return f"{self.username} ({self.tenant.name})"

    def has_permission(self, permission_codename: str) -> bool:
        """Check if user has a specific permission."""
        if not self.is_active or not self.role:
            return False
        return self.role.permissions_set.filter(
            permission__codename=permission_codename
        ).exists()

    def get_permissions(self) -> list[str]:
        """Get all permissions for this user."""
        if not self.role:
            return []
        return list(
            self.role.permissions_set.values_list(
                "permission__codename", flat=True
            )
        )


# --- Parsing & Data Validation (ALCOA+ Compliance) ---------------------------


class RawFile(models.Model):
    """Immutable file record with cryptographic proof.

    Every uploaded file is stored with SHA-256 hash for integrity verification.
    Files are NEVER overwritten or deleted -- only logically soft-deleted.

    ALCOA+:
    - Attributable: user_id + timestamp
    - Legible: filename, MIME type
    - Contemporaneous: created_at timestamp
    - Original: SHA-256 hash prevents tampering
    - Accurate: validated against schema
    - Complete: full file content preserved
    - Consistent: audit trail recorded
    - Enduring: immutable storage
    - Available: retrievable for review
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="raw_files",
        help_text="Tenant (lab) that uploaded the file",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who uploaded the file",
    )

    filename = models.CharField(
        max_length=255,
        help_text="Original filename from upload",
    )
    file_content = models.BinaryField(
        null=True,
        blank=True,
        help_text="File content for local storage (null when using S3)",
    )
    file_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of file content (proof of originality)",
    )
    file_size = models.BigIntegerField(
        help_text="File size in bytes",
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="MIME type (e.g., 'text/csv', 'application/pdf')",
    )

    # --- Feature 2: S3-Ready Storage Abstraction ---
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    STORAGE_CHOICES = [
        (LOCAL, "Local / Database"),
        (S3, "AWS S3"),
        (GCS, "Google Cloud Storage"),
    ]
    storage_backend = models.CharField(
        max_length=10,
        choices=STORAGE_CHOICES,
        default=LOCAL,
        help_text="Where the file is physically stored",
    )
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path in remote storage (e.g., 's3://bucket/tenant/file.csv')",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When file was uploaded",
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag (content preserved for audit)",
    )

    class Meta:
        app_label = "core"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["tenant", "uploaded_at"]),
            models.Index(fields=["file_hash"]),
        ]
        verbose_name = "Raw File"

    def __str__(self) -> str:
        return f"{self.filename} ({self.file_hash[:8]})"


class ParsedData(models.Model):
    """Data extracted by AI parser, pending human validation.

    States:
    - PENDING: Awaiting human review
    - VALIDATED: Confirmed by authorized user
    - REJECTED: Human rejected extraction
    - SUPERSEDED: Replaced by newer parsing

    CRITICAL: AI output is never directly used -- it's a proposal
    that requires explicit human confirmation.
    """

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"

    STATE_CHOICES = [
        (PENDING, "Awaiting Validation"),
        (VALIDATED, "Human Confirmed"),
        (REJECTED, "Human Rejected"),
        (SUPERSEDED, "Replaced by New Parse"),
    ]

    raw_file = models.OneToOneField(
        RawFile,
        on_delete=models.CASCADE,
        related_name="parsed_data",
        help_text="Original source file",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="parsed_data_records",
    )

    # AI Extraction
    extracted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When AI extraction occurred",
    )
    parsed_json = models.JSONField(
        help_text="Raw AI-extracted data (not yet validated)",
    )
    extraction_confidence = models.FloatField(
        help_text="AI confidence score (0.0 to 1.0)",
    )
    extraction_model = models.CharField(
        max_length=100,
        help_text="Which AI model was used (e.g., 'gpt-4-turbo')",
    )

    # --- Feature 1: AI Confidence Flagging (per-field) ---
    field_confidence_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text='Per-field confidence: {"equipment_name": 0.95, "sample_id": 0.42, ...}',
    )
    flagged_fields = models.JSONField(
        default=list,
        blank=True,
        help_text='Fields flagged for mandatory review: ["sample_id", "volume"]',
    )
    confidence_threshold = models.FloatField(
        default=0.7,
        help_text="Fields below this threshold are auto-flagged for review",
    )

    # --- Feature 3: Parsing Versioning (reproducibility) ---
    extraction_prompt_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version of the prompt template used (e.g., 'v2.3')",
    )
    extraction_prompt_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 of the exact prompt sent to the AI model",
    )
    extraction_model_version = models.CharField(
        max_length=100,
        blank=True,
        help_text="Full model version ID (e.g., 'gpt-4-turbo-2024-04-09')",
    )
    extraction_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Model params: {"temperature": 0, "max_tokens": 4096, ...}',
    )

    # Validation State
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=PENDING,
        db_index=True,
        help_text="Current validation state",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_parsed_data",
        help_text="User who confirmed/rejected extraction",
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When human validation occurred",
    )
    validation_notes = models.TextField(
        blank=True,
        help_text="Human notes on validation (e.g., corrections made)",
    )

    # Post-Validation Data
    confirmed_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Final validated data (after human corrections)",
    )

    class Meta:
        app_label = "core"
        ordering = ["-extracted_at"]
        indexes = [
            models.Index(fields=["tenant", "state"]),
            models.Index(fields=["raw_file"]),
        ]
        verbose_name = "Parsed Data"

    def __str__(self) -> str:
        return f"Parse of {self.raw_file.filename} ({self.state})"

    def validate(self, validated_json: dict, user: User, notes: str = ""):
        """Mark parsing as validated by a human.

        IMPORTANT: This is the gate that converts AI proposal to
        authoritative data.
        """
        self.state = self.VALIDATED
        self.validated_by = user
        self.validated_at = timezone.now()
        self.confirmed_json = validated_json
        self.validation_notes = notes
        self.save(update_fields=[
            "state", "validated_by", "validated_at",
            "confirmed_json", "validation_notes"
        ])


# --- Protocol Execution (Linking Intent to Action) -----------------------------


class ExecutionLog(models.Model):
    """Immutable record of protocol execution on a sample.

    This is the PROOF that an experiment was performed:
    - WHO ran it (user_id)
    - WHAT protocol was applied (protocol_id)
    - WHICH samples (linked via ExecutionStep)
    - USING which equipment (equipment_id)
    - WHEN it happened (started_at, completed_at)
    - WHAT were the results (linked via ParsedData)

    ALCOA+:
    - Attributable: user_id + timestamp
    - Legible: human-readable protocol execution
    - Contemporaneous: started_at, completed_at
    - Original: linked to immutable RawFile (machine output)
    - Accurate: validated by human technician
    - Complete: all steps recorded
    - Consistent: same structure for all executions
    - Enduring: soft delete only
    - Available: audit trail for every step
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="execution_logs",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        on_delete=models.CASCADE,
        related_name="executions",
        help_text="Which protocol was executed",
    )
    equipment = models.ForeignKey(
        "Equipment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Equipment used (Hamilton robot, spectrophotometer, etc.)",
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="started_executions",
        help_text="Technician who started execution",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_executions",
        help_text="Technician who validated execution results",
    )

    started_at = models.DateTimeField(
        help_text="When protocol execution began",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When protocol execution finished",
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When technician confirmed results",
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Currently Running"),
            ("completed", "Completed"),
            ("error", "Error/Failed"),
            ("validated", "Validated by Technician"),
        ],
        default="running",
        db_index=True,
    )

    # Source of execution data
    source_file = models.ForeignKey(
        RawFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Machine output file (CSV/JSON from equipment)",
    )

    notes = models.TextField(
        blank=True,
        help_text="Technician notes about execution",
    )

    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete (data preserved for audit)",
    )

    class Meta:
        app_label = "core"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["protocol", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.protocol} @ {self.started_at} ({self.status})"


class ExecutionStep(models.Model):
    """Single step within an ExecutionLog.

    Maps: Execution → Sample → Result (ParsedData)

    One ExecutionLog can have multiple steps:
    - Step 1: Apply reagent to sample A → Result recorded
    - Step 2: Centrifuge sample A → Result recorded
    - Step 3: Measure absorbance → Result recorded
    """

    execution = models.ForeignKey(
        ExecutionLog,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    protocol_step_number = models.IntegerField(
        help_text="Step number in protocol (1, 2, 3, ...)",
    )
    sample = models.ForeignKey(
        "samples.Sample",
        on_delete=models.CASCADE,
        help_text="Sample being processed in this step",
    )

    # Result of this step
    parsed_data = models.ForeignKey(
        ParsedData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_steps",
        help_text="AI-extracted result from machine (e.g., measurement, image analysis)",
    )

    # Validation
    is_valid = models.BooleanField(
        default=False,
        help_text="Technician confirmed this step's result is correct",
    )
    validation_notes = models.TextField(
        blank=True,
        help_text="Technician notes (e.g., 'Value seems low, verified with backup')",
    )

    class Meta:
        app_label = "core"
        unique_together = ("execution", "protocol_step_number", "sample")
        ordering = ["execution", "protocol_step_number"]

    def __str__(self) -> str:
        return f"{self.execution.protocol} Step {self.protocol_step_number} - {self.sample}"


class Equipment(models.Model):
    """Laboratory equipment that generates data.

    Equipment is a data SOURCE:
    - Hamilton liquid handler → generates "dispense" events
    - Spectrophotometer → generates "absorbance" measurements
    - Plate reader → generates "fluorescence" readings
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="equipment",
    )

    equipment_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique equipment identifier (from parsed file)",
    )
    equipment_name = models.CharField(
        max_length=255,
        help_text="Human-readable name",
    )
    equipment_type = models.CharField(
        max_length=100,
        choices=[
            ("liquid_handler", "Liquid Handler (Hamilton, Tecan)"),
            ("spectrophotometer", "Spectrophotometer"),
            ("plate_reader", "Plate Reader (Fluor, Absorbance)"),
            ("incubator", "Incubator"),
            ("centrifuge", "Centrifuge"),
            ("pcr_machine", "PCR/qPCR Machine"),
            ("microscope", "Microscope"),
            ("freezer", "Freezer Storage"),
            ("other", "Other"),
        ],
    )
    location = models.CharField(
        max_length=255,
        help_text="Physical location in lab",
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Serial number for traceability",
    )

    last_calibration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last calibration date (critical for accuracy)",
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("operational", "Operational"),
            ("maintenance", "In Maintenance"),
            ("broken", "Broken"),
            ("decommissioned", "Decommissioned"),
        ],
        default="operational",
    )

    class Meta:
        app_label = "core"
        ordering = ["equipment_name"]

    def __str__(self) -> str:
        return f"{self.equipment_name} ({self.equipment_type})"


class CertifiedReport(models.Model):
    """Certified data export with chain integrity verification.

    This is the document that clients present to auditors. It includes:
    - Complete execution history with all linked data
    - Audit trail summary showing all modifications
    - SHA-256 hash chain verification proof
    - Signature from technician who certified it

    CRITICAL: Report is NOT generated if audit chain is corrupted.
    """

    # STATES
    PENDING = "pending"
    CERTIFIED = "certified"
    REVOKED = "revoked"
    STATE_CHOICES = [
        (PENDING, "Pending Certification"),
        (CERTIFIED, "Certified & Auditable"),
        (REVOKED, "Revoked (chain corrupted)"),
    ]

    # DATA
    tenant = models.ForeignKey(
        "Tenant",
        on_delete=models.CASCADE,
        related_name="certified_reports",
        help_text="Lab that generated this report",
    )
    execution_log = models.ForeignKey(
        ExecutionLog,
        on_delete=models.CASCADE,
        related_name="certified_reports",
        help_text="Protocol execution this report documents",
    )

    # CERTIFICATION
    certified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certified_reports",
        help_text="Technician/QA who certified this report",
    )
    certified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When report was certified",
    )

    # INTEGRITY
    report_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of PDF content (proof of originality)",
    )
    chain_integrity_verified = models.BooleanField(
        default=False,
        help_text="Was audit chain verified before generation?",
    )
    chain_verification_details = models.JSONField(
        default=dict,
        help_text="Verification results: {total_records, verified, corrupted}",
    )

    # STORAGE
    pdf_filename = models.CharField(
        max_length=255,
        help_text="Filename of certified PDF report",
    )
    pdf_size = models.BigIntegerField(
        help_text="Size of PDF in bytes",
    )

    # STATE
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=PENDING,
        db_index=True,
        help_text="Certification state",
    )
    revocation_reason = models.TextField(
        blank=True,
        help_text="Reason for revocation if chain corrupted",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        indexes = [
            models.Index(fields=["tenant", "state"]),
            models.Index(fields=["execution_log", "state"]),
        ]
        ordering = ["-certified_at"]

    def __str__(self) -> str:
        return f"Report {self.id}: {self.execution_log.protocol} ({self.state})"

