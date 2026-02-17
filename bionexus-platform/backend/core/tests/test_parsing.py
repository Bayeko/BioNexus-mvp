"""Tests for file parsing with ALCOA+ compliance.

Verifies:
- File immutability (hash verification)
- Strict schema validation (no hallucinations)
- Human-in-the-loop validation
- Complete audit trail
"""

from django.test import TestCase
from pydantic import ValidationError

from core.models import RawFile, ParsedData, User
from core.parsing_service import FileHasher, ParsingService
from core.parsing_schemas import BatchExtractionResult, EquipmentData
from core.tests.fixtures import create_test_tenant, create_test_user
from core.audit import AuditTrail
from core.models import AuditLog


class FileHasherTest(TestCase):
    """Tests for file hashing and integrity verification."""

    def test_consistent_hash(self):
        """Same file content produces same hash."""
        content = b"Laboratory equipment data\nCentrifuge-001,SpinMax3000"
        hash1 = FileHasher.compute_hash(content)
        hash2 = FileHasher.compute_hash(content)
        self.assertEqual(hash1, hash2)

    def test_hash_change_on_modification(self):
        """Different content produces different hash."""
        content1 = b"Equipment A"
        content2 = b"Equipment B"
        self.assertNotEqual(
            FileHasher.compute_hash(content1),
            FileHasher.compute_hash(content2),
        )

    def test_integrity_verification(self):
        """Integrity check passes for matching hash."""
        content = b"Sample data"
        hash_val = FileHasher.compute_hash(content)
        self.assertTrue(FileHasher.verify_integrity(content, hash_val))

    def test_integrity_failure_on_tampering(self):
        """Integrity check fails if content changed."""
        original_content = b"Original"
        original_hash = FileHasher.compute_hash(original_content)

        tampered_content = b"Tampered"
        self.assertFalse(
            FileHasher.verify_integrity(tampered_content, original_hash)
        )


class FileUploadTest(TestCase):
    """Tests for file upload and immutability."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant)

    def test_upload_file_creates_rawfile(self):
        """File upload creates immutable RawFile record."""
        content = b"CSV data here"
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="equipment.csv",
            file_content=content,
            mime_type="text/csv",
        )

        self.assertIsNotNone(raw_file.id)
        self.assertEqual(raw_file.filename, "equipment.csv")
        self.assertEqual(raw_file.file_size, len(content))
        self.assertEqual(len(raw_file.file_hash), 64)  # SHA-256 hex = 64 chars

    def test_file_hash_immutable(self):
        """File hash is stored and can be verified."""
        content = b"Sample content"
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="test.txt",
            file_content=content,
            mime_type="text/plain",
        )

        expected_hash = FileHasher.compute_hash(content)
        self.assertEqual(raw_file.file_hash, expected_hash)

    def test_duplicate_file_returns_existing(self):
        """Uploading same file twice returns existing record."""
        content = b"Same content"
        file1 = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="file1.txt",
            file_content=content,
            mime_type="text/plain",
        )

        file2 = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="file2.txt",  # Different filename
            file_content=content,   # Same content
            mime_type="text/plain",
        )

        self.assertEqual(file1.id, file2.id)  # Same record

    def test_file_upload_creates_audit_log(self):
        """File upload is recorded in audit trail."""
        content = b"Audit test"
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="audit.txt",
            file_content=content,
            mime_type="text/plain",
        )

        logs = AuditLog.objects.filter(
            entity_type="RawFile",
            entity_id=raw_file.id,
            operation="CREATE",
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user_id, self.user.id)


class ParsingValidationTest(TestCase):
    """Tests for strict schema validation."""

    def test_valid_equipment_extraction(self):
        """Valid equipment data passes schema."""
        valid_data = {
            "equipment_id": "EQ-001",
            "equipment_name": "SpinMax 3000",
            "equipment_type": "centrifuge",
            "location": "Lab-A",
            "status": "operational",
        }
        equipment = EquipmentData(**valid_data)
        self.assertEqual(equipment.equipment_id, "EQ-001")

    def test_reject_invalid_equipment_type(self):
        """Invalid equipment type is rejected."""
        invalid_data = {
            "equipment_id": "EQ-001",
            "equipment_name": "Unknown Device",
            "equipment_type": "unknown_type",  # ❌ Not in allowed enum
            "location": "Lab-A",
        }
        with self.assertRaises(ValidationError):
            EquipmentData(**invalid_data)

    def test_reject_missing_required_field(self):
        """Missing required field is rejected."""
        incomplete_data = {
            "equipment_id": "EQ-001",
            # ❌ Missing equipment_name
            "equipment_type": "centrifuge",
            "location": "Lab-A",
        }
        with self.assertRaises(ValidationError):
            EquipmentData(**incomplete_data)

    def test_reject_extra_fields(self):
        """Extra fields are forbidden (no hallucinations)."""
        data_with_extra = {
            "equipment_id": "EQ-001",
            "equipment_name": "SpinMax",
            "equipment_type": "centrifuge",
            "location": "Lab-A",
            "hallucinated_field": "extra value",  # ❌ Not in schema
        }
        with self.assertRaises(ValidationError):
            EquipmentData(**data_with_extra)

    def test_strict_datetime_validation(self):
        """Invalid date format is rejected."""
        from core.parsing_schemas import SampleData

        invalid_date = {
            "sample_id": "S-001",
            "sample_name": "Blood Sample",
            "sample_type": "blood",
            "collected_at": "2026/02/17",  # ❌ Wrong format
            "collected_by": "John",
        }
        with self.assertRaises(ValidationError):
            SampleData(**invalid_date)


class ParsingWorkflowTest(TestCase):
    """Tests for complete parsing workflow."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.uploader = create_test_user(tenant=self.tenant, username="uploader")
        self.validator = create_test_user(tenant=self.tenant, username="validator")

    def test_file_upload_to_validation_workflow(self):
        """Complete workflow: upload → parse → validate."""
        # Step 1: Upload
        content = b"equipment data"
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.uploader,
            filename="data.txt",
            file_content=content,
            mime_type="text/plain",
        )
        self.assertIsNotNone(raw_file.id)

        # Step 2: AI extraction
        ai_data = {
            "equipment_records": [
                {
                    "equipment_id": "EQ-001",
                    "equipment_name": "Centrifuge A",
                    "equipment_type": "centrifuge",
                    "location": "Lab-1",
                    "status": "operational",
                }
            ],
            "sample_records": [],
            "extraction_warnings": [],
        }
        parsed = ParsingService.parse_file(
            raw_file=raw_file,
            ai_extracted_data=ai_data,
            model_name="gpt-4",
            confidence_score=0.95,
        )
        self.assertEqual(parsed.state, ParsedData.PENDING)

        # Step 3: Human validation
        validated = ParsingService.validate_and_confirm(
            parsed_data=parsed,
            validator_user=self.validator,
            confirmed_json=ai_data,
            validation_notes="Data looks correct",
        )
        self.assertEqual(validated.state, ParsedData.VALIDATED)

        # Verify audit trail
        logs = AuditLog.objects.filter(entity_type="ParsedData")
        self.assertGreaterEqual(logs.count(), 2)  # CREATE + UPDATE

    def test_rejection_workflow(self):
        """Workflow: upload → parse → reject."""
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.uploader,
            filename="bad_data.txt",
            file_content=b"corrupted",
            mime_type="text/plain",
        )

        ai_data = {
            "equipment_records": [],
            "sample_records": [],
            "extraction_warnings": ["Could not parse file"],
        }
        parsed = ParsingService.parse_file(
            raw_file=raw_file,
            ai_extracted_data=ai_data,
        )

        rejected = ParsingService.reject_parsing(
            parsed_data=parsed,
            validator_user=self.validator,
            rejection_reason="File corrupted, cannot parse",
        )
        self.assertEqual(rejected.state, ParsedData.REJECTED)

        # Verify audit trail shows rejection
        logs = AuditLog.objects.filter(
            entity_type="ParsedData",
            entity_id=parsed.id,
            operation="UPDATE",
        )
        self.assertTrue(logs.exists())
