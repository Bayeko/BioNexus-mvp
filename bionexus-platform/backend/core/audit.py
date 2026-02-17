"""Audit trail utilities for 21 CFR Part 11 compliance.

This module provides the low-level machinery for recording and verifying
audit trails. Higher-level services use this to record mutations.
"""

from datetime import datetime
from typing import Any

from django.db import transaction

from .models import AuditLog


class AuditTrail:
    """Manages audit log creation with cryptographic signature chaining."""

    @staticmethod
    def record(
        entity_type: str,
        entity_id: int,
        operation: str,
        changes: dict[str, Any],
        snapshot_before: dict[str, Any],
        snapshot_after: dict[str, Any],
        user_id: int | None = None,
        user_email: str | None = None,
    ) -> AuditLog:
        """Record a mutation in the audit trail with signature.

        This method:
        1. Fetches the last audit record for this entity type
        2. Calculates the new signature (chaining to previous)
        3. Creates an immutable AuditLog record
        4. Returns the audit log for reference

        Args:
            entity_type: Name of the model (e.g., 'Sample', 'Protocol')
            entity_id: Primary key of the affected entity
            operation: 'CREATE', 'UPDATE', or 'DELETE'
            changes: Dict of field changes, e.g.,
                     {'name': {'before': 'Old', 'after': 'New'}}
            snapshot_before: Complete entity state before mutation (for forensics)
            snapshot_after: Complete entity state after mutation
            user_id: ID of the user who triggered the mutation (optional for MVP)
            user_email: Email of the user (optional for MVP)

        Returns:
            AuditLog: The immutable audit record just created

        Raises:
            ValueError: If signature validation fails
        """
        with transaction.atomic():
            from django.utils import timezone

            # Get the last audit record for this entity type (to chain signatures)
            last_log = (
                AuditLog.objects.filter(entity_type=entity_type)
                .order_by("-timestamp", "-id")
                .first()
            )

            previous_signature = last_log.signature if last_log else None
            now = timezone.now()
            # Remove microseconds for deterministic signature (timestamps don't need that precision)
            now = now.replace(microsecond=0)
            now_iso = now.isoformat()

            # Calculate signature (chains to previous)
            signature = AuditLog.calculate_signature(
                previous_signature=previous_signature,
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                changes=changes,
                timestamp=now_iso,
            )

            # Create the immutable record with timestamp already set
            audit_log = AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                changes=changes,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
                user_id=user_id,
                user_email=user_email,
                signature=signature,
                previous_signature=previous_signature,
                timestamp=now,  # Set timestamp before save
            )
            audit_log.save()
            return audit_log

    @staticmethod
    def get_entity_history(entity_type: str, entity_id: int) -> list[AuditLog]:
        """Fetch the complete audit history for an entity.

        Returns all mutations for the entity, ordered chronologically.
        """
        return list(
            AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id)
            .order_by("timestamp", "id")
        )

    @staticmethod
    def verify_chain_integrity(entity_type: str) -> tuple[bool, str]:
        """Verify that the audit chain has not been tampered with.

        Walks the entire audit chain for a given entity type, verifying that
        each record's signature correctly chains to its predecessor. If any
        record is modified, its signature becomes invalid.

        Returns:
            (is_valid, message)
                is_valid: True if chain is intact, False if tampering detected
                message: Human-readable explanation
        """
        logs = list(
            AuditLog.objects.filter(entity_type=entity_type)
            .order_by("timestamp", "id")
        )

        if not logs:
            return True, f"No audit logs for {entity_type} (empty history is valid)"

        for i, log in enumerate(logs):
            expected_previous = logs[i - 1].signature if i > 0 else None
            if log.previous_signature != expected_previous:
                return (
                    False,
                    f"Chain broken at log #{log.id}: "
                    f"expected previous_signature={expected_previous}, "
                    f"got {log.previous_signature}",
                )

            # Recalculate signature to detect tampering
            expected_signature = AuditLog.calculate_signature(
                previous_signature=log.previous_signature,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                operation=log.operation,
                changes=log.changes,
                timestamp=log.timestamp.isoformat(),
            )
            if log.signature != expected_signature:
                return (
                    False,
                    f"Tampering detected in log #{log.id}: "
                    f"expected signature={expected_signature}, got {log.signature}",
                )

        return True, f"Chain integrity verified for {len(logs)} records"

    @staticmethod
    def get_latest_signature(entity_type: str) -> str | None:
        """Get the most recent signature for an entity type (chain tip)."""
        last_log = (
            AuditLog.objects.filter(entity_type=entity_type)
            .order_by("-timestamp", "-id")
            .values_list("signature", flat=True)
            .first()
        )
        return last_log
