"""Tests for protocol execution and result linkage (no orphaned data).

Verifies:
- ExecutionLog creation and step management
- Result linkage to samples (traceability)
- Orphaned data detection
- Technician validation gate
- Complete audit trail
"""

from django.test import TestCase
from django.utils import timezone

from core.audit import AuditTrail
from core.models import AuditLog, ExecutionLog, ExecutionStep, Equipment
from core.execution_service import ProtocolExecutionService
from core.tests.fixtures import create_test_tenant, create_test_user
from modules.samples.models import Sample
from modules.protocols.models import Protocol


class ExecutionStartTest(TestCase):
    """Tests for starting a protocol execution."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant, username="tech1")

        # Create protocol and sample
        self.protocol = Protocol.objects.create(
            title="DNA Extraction",
            description="Standard DNA extraction protocol",
        )
        self.sample = Sample.objects.create(
            name="Sample A",
            sample_type="blood",
            received_at=timezone.now(),
            location="Freezer 1",
        )

    def test_start_execution(self):
        """Starting execution creates ExecutionLog."""
        execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=self.protocol,
            user=self.user,
        )

        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.protocol_id, self.protocol.id)
        self.assertEqual(execution.started_by_id, self.user.id)
        self.assertEqual(execution.status, "running")

    def test_execution_creates_audit_log(self):
        """Execution start is recorded in audit trail."""
        execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=self.protocol,
            user=self.user,
        )

        logs = AuditLog.objects.filter(
            entity_type="ExecutionLog",
            entity_id=execution.id,
            operation="CREATE",
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user_id, self.user.id)


class ExecutionStepTest(TestCase):
    """Tests for adding steps with result linkage."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant)

        self.protocol = Protocol.objects.create(
            title="Test Protocol",
            description="",
        )
        self.sample = Sample.objects.create(
            name="Sample B",
            sample_type="plasma",
            received_at=timezone.now(),
            location="Freezer 2",
        )

        # Create equipment
        self.equipment = Equipment.objects.create(
            tenant=self.tenant,
            equipment_id="SPEC-001",
            equipment_name="Spectrophotometer A",
            equipment_type="spectrophotometer",
            location="Lab-B",
        )

        # Start execution
        self.execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=self.protocol,
            user=self.user,
            equipment=self.equipment,
        )

    def test_add_step_creates_link(self):
        """Adding step creates ExecutionStep with sample link."""
        step = ProtocolExecutionService.add_step_result(
            execution=self.execution,
            step_number=1,
            sample_id=self.sample.id,
        )

        self.assertEqual(step.execution_id, self.execution.id)
        self.assertEqual(step.sample_id, self.sample.id)
        self.assertEqual(step.protocol_step_number, 1)

    def test_step_creates_audit_log(self):
        """Adding step is recorded in audit trail."""
        step = ProtocolExecutionService.add_step_result(
            execution=self.execution,
            step_number=1,
            sample_id=self.sample.id,
        )

        logs = AuditLog.objects.filter(
            entity_type="ExecutionStep",
            entity_id=step.id,
        )
        self.assertEqual(logs.count(), 1)


class ResultLinkageTest(TestCase):
    """Tests for linking ParsedData to ExecutionStep."""

    def setUp(self):
        from core.parsing_service import ParsingService

        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant)

        # Setup execution
        self.protocol = Protocol.objects.create(title="Test")
        self.sample = Sample.objects.create(
            name="Sample C",
            sample_type="serum",
            received_at=timezone.now(),
            location="Freezer 3",
        )
        self.execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=self.protocol,
            user=self.user,
        )

        # Create a validated ParsedData (simulating AI extraction + human approval)
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="results.csv",
            file_content=b"absorbance,405nm\n0.125",
            mime_type="text/csv",
        )

        ai_data = {
            "equipment_records": [],
            "sample_records": [],
        }
        self.parsed_data = ParsingService.parse_file(
            raw_file=raw_file,
            ai_extracted_data=ai_data,
        )

        # Validate it
        ParsingService.validate_and_confirm(
            parsed_data=self.parsed_data,
            validator_user=self.user,
            confirmed_json=ai_data,
        )

    def test_link_result_to_step(self):
        """Linking ParsedData to ExecutionStep traces result."""
        step = ProtocolExecutionService.add_step_result(
            execution=self.execution,
            step_number=1,
            sample_id=self.sample.id,
            parsed_data=self.parsed_data,
        )

        self.assertEqual(step.parsed_data_id, self.parsed_data.id)
        self.assertEqual(step.sample_id, self.sample.id)

    def test_retroactive_linkage(self):
        """Can retroactively link ParsedData to existing step."""
        # Create step without data first
        step = ProtocolExecutionService.add_step_result(
            execution=self.execution,
            step_number=1,
            sample_id=self.sample.id,
            parsed_data=None,
        )

        # Then link data later
        updated = ProtocolExecutionService.link_parsed_data_to_step(
            step=step,
            parsed_data=self.parsed_data,
        )

        self.assertEqual(updated.parsed_data_id, self.parsed_data.id)


class OrphanedDataDetectionTest(TestCase):
    """Tests for finding unlinked (orphaned) results."""

    def setUp(self):
        from core.parsing_service import ParsingService

        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant)

        # Create a validated ParsedData but DON'T link it
        raw_file = ParsingService.upload_file(
            tenant=self.tenant,
            user=self.user,
            filename="orphan.csv",
            file_content=b"data",
            mime_type="text/csv",
        )

        ai_data = {
            "equipment_records": [],
            "sample_records": [],
        }
        parsed = ParsingService.parse_file(
            raw_file=raw_file,
            ai_extracted_data=ai_data,
        )

        ParsingService.validate_and_confirm(
            parsed_data=parsed,
            validator_user=self.user,
            confirmed_json=ai_data,
        )

        self.orphaned_data = parsed

    def test_detect_orphaned_data(self):
        """Orphaned (unlinked) data is detected."""
        orphans = ProtocolExecutionService.get_orphaned_parsed_data(self.tenant)
        self.assertIn(self.orphaned_data, orphans)

    def test_linking_removes_from_orphans(self):
        """Linking data to step removes from orphans list."""
        protocol = Protocol.objects.create(title="Link Test")
        sample = Sample.objects.create(
            name="Sample D",
            sample_type="dna",
            received_at=timezone.now(),
            location="Freezer 4",
        )

        execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=protocol,
            user=self.user,
        )

        # Before linking
        orphans_before = ProtocolExecutionService.get_orphaned_parsed_data(
            self.tenant
        )
        self.assertIn(self.orphaned_data, orphans_before)

        # Link it
        ProtocolExecutionService.add_step_result(
            execution=execution,
            step_number=1,
            sample_id=sample.id,
            parsed_data=self.orphaned_data,
        )

        # After linking
        orphans_after = ProtocolExecutionService.get_orphaned_parsed_data(
            self.tenant
        )
        self.assertNotIn(self.orphaned_data, orphans_after)


class TechnicianValidationTest(TestCase):
    """Tests for technician review of results."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.tech = create_test_user(tenant=self.tenant, username="tech_john")
        self.validator = create_test_user(
            tenant=self.tenant, username="validator_jane"
        )

        protocol = Protocol.objects.create(title="Validation Test")
        sample = Sample.objects.create(
            name="Sample E",
            sample_type="rna",
            received_at=timezone.now(),
            location="Freezer 5",
        )

        execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=protocol,
            user=self.tech,
        )

        self.step = ProtocolExecutionService.add_step_result(
            execution=execution,
            step_number=1,
            sample_id=sample.id,
        )

    def test_validate_step(self):
        """Technician can validate a step result."""
        validated = ProtocolExecutionService.validate_step(
            step=self.step,
            validator=self.validator,
            is_valid=True,
            validation_notes="Result matches expected range",
        )

        self.assertTrue(validated.is_valid)
        self.assertEqual(
            validated.validation_notes, "Result matches expected range"
        )

    def test_reject_step(self):
        """Technician can reject invalid result."""
        rejected = ProtocolExecutionService.validate_step(
            step=self.step,
            validator=self.validator,
            is_valid=False,
            validation_notes="Value too high, rerun needed",
        )

        self.assertFalse(rejected.is_valid)
        self.assertIn("rerun", rejected.validation_notes)

    def test_validation_creates_audit_log(self):
        """Validation decision is recorded."""
        ProtocolExecutionService.validate_step(
            step=self.step,
            validator=self.validator,
            is_valid=True,
        )

        logs = AuditLog.objects.filter(
            entity_type="ExecutionStep",
            entity_id=self.step.id,
            operation="UPDATE",
        )
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().user_id, self.validator.id)


class CompleteExecutionTest(TestCase):
    """Tests for completing execution."""

    def setUp(self):
        self.tenant = create_test_tenant()
        self.user = create_test_user(tenant=self.tenant)

        self.execution = ProtocolExecutionService.start_execution(
            tenant=self.tenant,
            protocol=Protocol.objects.create(title="Complete Test"),
            user=self.user,
        )

    def test_complete_execution(self):
        """Completing sets status and timestamp."""
        completed = ProtocolExecutionService.complete_execution(
            execution=self.execution,
            user=self.user,
            notes="All steps completed successfully",
        )

        self.assertEqual(completed.status, "completed")
        self.assertIsNotNone(completed.completed_at)
        self.assertEqual(completed.notes, "All steps completed successfully")
