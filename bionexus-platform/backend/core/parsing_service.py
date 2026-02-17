"""Parsing service for file processing with ALCOA+ compliance.

Architecture:
1. File Hash (immutability proof)
2. AI Extraction (proposal only)
3. Schema Validation (strict enforcement)
4. Human Review (gate before acceptance)
5. Audit Trail (every step recorded)

No data is ever accepted without human authorization.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from django.utils import timezone
from pydantic import ValidationError

from .models import RawFile, ParsedData, Tenant, User
from .parsing_schemas import BatchExtractionResult, EquipmentData, SampleData
from .audit import AuditTrail


class FileHasher:
    """Handles file hashing for immutability verification."""

    @staticmethod
    def compute_hash(file_content: bytes) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            file_content: Raw file bytes

        Returns:
            Hexadecimal SHA-256 digest
        """
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    def verify_integrity(file_content: bytes, known_hash: str) -> bool:
        """Verify file hasn't been tampered with.

        Args:
            file_content: Current file content
            known_hash: Expected hash from audit trail

        Returns:
            True if hash matches (file is intact)
        """
        current_hash = FileHasher.compute_hash(file_content)
        return current_hash == known_hash


class ParsingService:
    """Orchestrates file parsing with validation and audit trail.

    Principles:
    - AI is a tool, not authority
    - All AI output must be validated by schema
    - All AI output must be approved by human
    - Every step is immutably recorded
    """

    @staticmethod
    def upload_file(
        tenant: Tenant,
        user: User,
        filename: str,
        file_content: bytes,
        mime_type: str,
    ) -> RawFile:
        """Store uploaded file with integrity hash.

        This is STEP 1: Capture the original, immutable source.

        Args:
            tenant: Tenant organization
            user: User uploading file
            filename: Original filename
            file_content: Raw file bytes
            mime_type: MIME type (e.g., 'text/csv')

        Returns:
            RawFile record (immutable)

        Audit Trail: Records file upload with hash
        """
        file_hash = FileHasher.compute_hash(file_content)

        # Check for duplicate uploads (same hash = same content)
        existing = RawFile.objects.filter(file_hash=file_hash).first()
        if existing:
            return existing  # Return existing instead of duplicate

        raw_file = RawFile.objects.create(
            tenant=tenant,
            user=user,
            filename=filename,
            file_content=file_content,
            file_hash=file_hash,
            file_size=len(file_content),
            mime_type=mime_type,
        )

        # Audit: File uploaded
        AuditTrail.record(
            entity_type="RawFile",
            entity_id=raw_file.id,
            operation="CREATE",
            changes={
                "filename": {"before": None, "after": filename},
                "file_hash": {"before": None, "after": file_hash},
            },
            snapshot_before={},
            snapshot_after={
                "id": raw_file.id,
                "filename": filename,
                "file_hash": file_hash,
                "file_size": len(file_content),
                "mime_type": mime_type,
            },
            user_id=user.id,
            user_email=user.email,
        )

        return raw_file

    @staticmethod
    def parse_file(
        raw_file: RawFile,
        ai_extracted_data: dict,
        model_name: str = "gpt-4-turbo",
        confidence_score: float = 0.9,
    ) -> ParsedData:
        """Validate AI extraction against strict schema.

        This is STEP 2: Capture AI proposal (not yet accepted).

        The AI output is validated against Pydantic schemas.
        Any deviation causes immediate rejection.

        Args:
            raw_file: Original file
            ai_extracted_data: Raw output from AI
            model_name: Which AI model was used
            confidence_score: AI confidence (0.0 to 1.0)

        Returns:
            ParsedData record (state=PENDING)

        Raises:
            ValidationError: If AI output doesn't match schema

        Audit Trail: Records parse attempt (BEFORE validation)
        """
        try:
            # STRICT validation: extra fields forbidden, type enforcement
            validated = BatchExtractionResult(**ai_extracted_data)
            is_schema_valid = True
            validation_error = None
        except ValidationError as e:
            is_schema_valid = False
            validation_error = str(e)
            # Still create ParsedData record so human can review what failed
            validated = None

        parsed_data = ParsedData.objects.create(
            raw_file=raw_file,
            tenant=raw_file.tenant,
            parsed_json=ai_extracted_data,
            extraction_confidence=confidence_score,
            extraction_model=model_name,
            state=ParsedData.PENDING,  # ← Awaiting human review
        )

        # Audit: AI extraction attempt
        AuditTrail.record(
            entity_type="ParsedData",
            entity_id=parsed_data.id,
            operation="CREATE",
            changes={
                "state": {"before": None, "after": "PENDING"},
                "extraction_model": {"before": None, "after": model_name},
                "schema_valid": {"before": None, "after": is_schema_valid},
            },
            snapshot_before={},
            snapshot_after={
                "id": parsed_data.id,
                "raw_file_id": raw_file.id,
                "state": "PENDING",
                "schema_valid": is_schema_valid,
                "validation_error": validation_error,
            },
            user_id=raw_file.user.id,
            user_email=raw_file.user.email,
        )

        if not is_schema_valid:
            raise ValidationError(validation_error)

        return parsed_data

    @staticmethod
    def validate_and_confirm(
        parsed_data: ParsedData,
        validator_user: User,
        confirmed_json: Optional[dict] = None,
        validation_notes: str = "",
    ) -> ParsedData:
        """Human confirms (or rejects) AI-extracted data.

        This is STEP 3: Gate that authorizes data acceptance.

        The human can:
        - Accept AI data as-is (confirmed_json=None)
        - Accept with corrections (confirmed_json=corrected_data)
        - Reject (calls reject() instead)

        Args:
            parsed_data: ParsedData record to validate
            validator_user: User confirming (must have permission)
            confirmed_json: Human-corrected data (if different from AI)
            validation_notes: Why human approved/modified

        Returns:
            Updated ParsedData (state=VALIDATED)

        Audit Trail: Records human validation decision
        """
        if confirmed_json is None:
            # Use AI data as-is
            confirmed_json = parsed_data.parsed_json

        # Final schema validation on confirmed data
        try:
            final_data = BatchExtractionResult(**confirmed_json)
        except ValidationError as e:
            raise ValueError(f"Confirmed data doesn't match schema: {e}")

        # Record the validation event
        parsed_data.validate(
            validated_json=confirmed_json,
            user=validator_user,
            notes=validation_notes,
        )

        # Audit: Human confirmed data
        AuditTrail.record(
            entity_type="ParsedData",
            entity_id=parsed_data.id,
            operation="UPDATE",
            changes={
                "state": {"before": "PENDING", "after": "VALIDATED"},
                "validated_by_id": {
                    "before": None,
                    "after": validator_user.id,
                },
            },
            snapshot_before={
                "state": "PENDING",
                "parsed_json_keys": list(parsed_data.parsed_json.keys()),
            },
            snapshot_after={
                "state": "VALIDATED",
                "validated_by_id": validator_user.id,
                "confirmed_json_keys": list(confirmed_json.keys()),
            },
            user_id=validator_user.id,
            user_email=validator_user.email,
        )

        return parsed_data

    @staticmethod
    def reject_parsing(
        parsed_data: ParsedData,
        validator_user: User,
        rejection_reason: str,
    ) -> ParsedData:
        """Human rejects AI extraction.

        Reason might be:
        - "Too many extraction errors"
        - "Schema violations in 3 rows"
        - "Data quality insufficient"

        Args:
            parsed_data: ParsedData to reject
            validator_user: User rejecting
            rejection_reason: Why it was rejected

        Returns:
            Updated ParsedData (state=REJECTED)

        Audit Trail: Records rejection decision
        """
        parsed_data.reject(validator_user, rejection_reason)

        # Audit: Human rejected data
        AuditTrail.record(
            entity_type="ParsedData",
            entity_id=parsed_data.id,
            operation="UPDATE",
            changes={
                "state": {"before": "PENDING", "after": "REJECTED"},
                "rejection_reason": {
                    "before": None,
                    "after": rejection_reason,
                },
            },
            snapshot_before={"state": "PENDING"},
            snapshot_after={
                "state": "REJECTED",
                "rejection_reason": rejection_reason,
            },
            user_id=validator_user.id,
            user_email=validator_user.email,
        )

        return parsed_data

    @staticmethod
    def get_pending_validations(tenant: Tenant) -> list[ParsedData]:
        """Get all parses awaiting human review for a tenant."""
        return ParsedData.objects.filter(
            tenant=tenant,
            state=ParsedData.PENDING,
        ).order_by("extracted_at")
