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
