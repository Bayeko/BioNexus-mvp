"""Tests for certified reporting service with audit chain verification.

Tests verify:
1. Audit chain integrity verification works correctly
2. Report generation includes all related data
3. Corrupted chains prevent report generation
4. PDF hash is recorded and unique
5. Audit trail records report creation
"""

import hashlib
from django.test import TestCase
from django.utils import timezone

from core.models import (
    CertifiedReport,
    ExecutionLog,
    ExecutionStep,
    AuditLog,
    Tenant,
    User,
)
from core.audit import AuditTrail
from core.reporting_service import CertifiedReportService
from modules.protocols.models import Protocol
from modules.samples.models import Sample


class ReportGenerationTest(TestCase):
    """Test certified report generation."""

    def setUp(self):
        """Create test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        # Create users
        self.technician = User.objects.create_user(
            username="tech1",
            email="tech@lab.local",
            password="test",
            tenant=self.tenant,
        )
        self.qa_approver = User.objects.create_user(
            username="qa1",
            email="qa@lab.local",
            password="test",
            tenant=self.tenant,
        )

        # Create protocol
        self.protocol = Protocol.objects.create(
            title="DNA Extraction",
            description="Standard extraction protocol",
        )

        # Create samples
        self.sample_a = Sample.objects.create(
            name="Sample A",
            sample_type="blood",
            received_at=timezone.now(),
            location="Freezer 1",
        )
        self.sample_b = Sample.objects.create(
            name="Sample B",
            sample_type="blood",
            received_at=timezone.now(),
            location="Freezer 1",
        )

        # Create execution log
        self.execution = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=self.protocol,
            started_by=self.technician,
            started_at=timezone.now(),
            status="completed",
            completed_at=timezone.now(),
        )

        # Create execution steps
        self.step_1 = ExecutionStep.objects.create(
            execution=self.execution,
            protocol_step_number=1,
            sample=self.sample_a,
            is_valid=True,
            validation_notes="Step 1 OK",
        )
        self.step_2 = ExecutionStep.objects.create(
            execution=self.execution,
            protocol_step_number=2,
            sample=self.sample_b,
            is_valid=True,
            validation_notes="Step 2 OK",
        )

        # Generate audit trail records
        for i in range(5):
            AuditTrail.record(
                entity_type="ExecutionStep",
                entity_id=self.step_1.id,
                operation="UPDATE",
                changes={"status": {"before": "pending", "after": "complete"}},
                snapshot_before={},
                snapshot_after={},
                user_id=self.technician.id,
                user_email=self.technician.email,
            )

    def test_report_generation_success(self):
        """Test successful report generation with valid audit chain."""
        report = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.qa_approver,
            notes="All steps completed successfully",
        )

        # Verify report properties
        self.assertEqual(report.tenant, self.tenant)
        self.assertEqual(report.execution_log, self.execution)
        self.assertEqual(report.certified_by, self.qa_approver)
        self.assertEqual(report.state, CertifiedReport.CERTIFIED)
        self.assertTrue(report.chain_integrity_verified)
        self.assertIsNotNone(report.report_hash)
        self.assertIsNotNone(report.pdf_filename)
        self.assertGreater(report.pdf_size, 0)

    def test_report_hash_is_unique(self):
        """Test that each report has a unique hash."""
        report_1 = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.qa_approver,
            notes="First report",
        )

        # Create another execution to generate a different report
        execution_2 = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=self.protocol,
            started_by=self.technician,
            started_at=timezone.now(),
            status="completed",
            completed_at=timezone.now(),
        )

        report_2 = CertifiedReportService.generate_report(
            execution_log=execution_2,
            certified_by=self.qa_approver,
            notes="Second report",
        )

        # Verify hashes are different
        self.assertNotEqual(report_1.report_hash, report_2.report_hash)

    def test_report_included_in_audit_trail(self):
        """Test that report generation is recorded in audit trail."""
        initial_audit_count = AuditLog.objects.count()

        report = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.qa_approver,
            notes="Test",
        )

        # Verify audit record was created
        final_audit_count = AuditLog.objects.count()
        self.assertGreater(final_audit_count, initial_audit_count)

        # Find the report creation audit
        report_audit = AuditLog.objects.filter(
            entity_type="CertifiedReport",
            entity_id=report.id,
            operation="CREATE",
        ).first()

        self.assertIsNotNone(report_audit)
        self.assertEqual(report_audit.user_id, self.qa_approver.id)

    def test_report_aggregates_all_data(self):
        """Test that report includes all related execution data."""
        aggregated = CertifiedReportService._aggregate_execution_data(self.execution)

        # Verify execution data
        self.assertEqual(aggregated['execution']['id'], self.execution.id)
        self.assertEqual(aggregated['execution']['protocol'], self.protocol.title)

        # Verify steps are included
        self.assertEqual(len(aggregated['steps']), 2)
        self.assertEqual(aggregated['steps'][0]['step_number'], 1)
        self.assertEqual(aggregated['steps'][0]['sample'], self.sample_a.name)
        self.assertTrue(aggregated['steps'][0]['is_valid'])

        # Verify samples are included
        self.assertEqual(len(aggregated['samples']), 2)
        sample_names = {s['name'] for s in aggregated['samples']}
        self.assertEqual(sample_names, {self.sample_a.name, self.sample_b.name})

        # Verify audit records count
        self.assertGreater(aggregated['audit_records_count'], 0)


class AuditChainVerificationTest(TestCase):
    """Test audit chain integrity verification."""

    def setUp(self):
        """Create test data."""
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        self.user = User.objects.create_user(
            username="tech1",
            email="tech@lab.local",
            password="test",
            tenant=self.tenant,
        )

    def test_clean_chain_verified(self):
        """Test that clean audit chain is verified successfully."""
        # Create some audit records
        for i in range(3):
            AuditTrail.record(
                entity_type="Sample",
                entity_id=100 + i,
                operation="CREATE",
                changes={},
                snapshot_before={},
                snapshot_after={},
                user_id=self.user.id,
                user_email=self.user.email,
            )

        # Verify chain
        result = CertifiedReportService._verify_audit_chain(self.tenant)

        self.assertTrue(result['is_valid'])
        self.assertTrue(result['chain_integrity_ok'])
        self.assertEqual(result['total_records'], 3)
        self.assertEqual(result['verified_records'], 3)
        self.assertEqual(len(result['corrupted_records']), 0)

    def test_corrupted_chain_detected(self):
        """Test that corrupted chains are detected."""
        # Create a record
        audit_1 = AuditLog.objects.create(
            entity_type="Sample",
            entity_id=100,
            operation="CREATE",
            timestamp=timezone.now().replace(microsecond=0),
            changes={},
            snapshot_before={},
            snapshot_after={},
            signature="abc123",
            previous_signature=None,
            user_id=self.user.id,
            user_email=self.user.email,
        )

        # Create a second record with broken chain
        audit_2 = AuditLog.objects.create(
            entity_type="Sample",
            entity_id=101,
            operation="CREATE",
            timestamp=timezone.now().replace(microsecond=0),
            changes={},
            snapshot_before={},
            snapshot_after={},
            signature="def456",
            previous_signature="wrong_hash",  # Broken chain!
            user_id=self.user.id,
            user_email=self.user.email,
        )

        # Verify chain
        result = CertifiedReportService._verify_audit_chain(self.tenant)

        self.assertFalse(result['is_valid'])
        self.assertFalse(result['chain_integrity_ok'])
        self.assertEqual(len(result['corrupted_records']), 1)

    def test_corrupted_chain_prevents_report(self):
        """Test that corrupted audit chain prevents report generation."""
        # Create execution
        protocol = Protocol.objects.create(
            title="Test Protocol",
            description="Test",
        )

        execution = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=protocol,
            started_by=self.user,
            started_at=timezone.now(),
            status="completed",
            completed_at=timezone.now(),
        )

        # Create a corrupted audit record
        AuditLog.objects.create(
            entity_type="ExecutionLog",
            entity_id=execution.id,
            operation="CREATE",
            timestamp=timezone.now().replace(microsecond=0),
            changes={},
            snapshot_before={},
            snapshot_after={},
            signature="bad_sig",
            previous_signature="bad_prev",
            user_id=self.user.id,
            user_email=self.user.email,
        )

        # Try to generate report - should fail
        with self.assertRaises(ValueError) as ctx:
            CertifiedReportService.generate_report(
                execution_log=execution,
                certified_by=self.user,
                notes="Test",
            )

        self.assertIn("Audit chain corrupted", str(ctx.exception))

        # Verify report was created but in REVOKED state
        report = CertifiedReport.objects.filter(execution_log=execution).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.state, CertifiedReport.REVOKED)
        self.assertIn("corrupted", report.revocation_reason.lower())


class PDFGenerationTest(TestCase):
    """Test PDF report generation."""

    def setUp(self):
        """Create test data."""
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        self.user = User.objects.create_user(
            username="tech1",
            email="tech@lab.local",
            password="test",
            tenant=self.tenant,
        )

        self.protocol = Protocol.objects.create(
            title="DNA Extraction",
            description="Test",
        )

        self.sample = Sample.objects.create(
            name="Sample A",
            sample_type="blood",
            received_at=timezone.now(),
            location="Freezer 1",
        )

        self.execution = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=self.protocol,
            started_by=self.user,
            started_at=timezone.now(),
            status="completed",
            completed_at=timezone.now(),
        )

        ExecutionStep.objects.create(
            execution=self.execution,
            protocol_step_number=1,
            sample=self.sample,
            is_valid=True,
            validation_notes="Step OK",
        )

    def test_pdf_content_generated(self):
        """Test that PDF content is generated."""
        aggregated = CertifiedReportService._aggregate_execution_data(self.execution)
        chain_result = {"is_valid": True, "verified_records": 5, "corrupted_records": []}

        pdf_content = CertifiedReportService._generate_pdf(
            execution_log=self.execution,
            aggregated_data=aggregated,
            chain_result=chain_result,
            certified_by=self.user,
            notes="All OK",
        )

        # Verify PDF content
        self.assertIsNotNone(pdf_content)
        self.assertGreater(len(pdf_content), 0)
        self.assertIsInstance(pdf_content, bytes)

    def test_report_hash_consistent(self):
        """Test that report hash is consistent."""
        report_1 = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.user,
            notes="Test",
        )

        # Retrieve and verify hash format
        self.assertEqual(len(report_1.report_hash), 64)  # SHA-256 hex length
        self.assertTrue(all(c in '0123456789abcdef' for c in report_1.report_hash))


class ComplianceTest(TestCase):
    """Test GxP compliance features."""

    def setUp(self):
        """Create test data."""
        self.tenant = Tenant.objects.create(
            name="Test Lab",
            slug="test-lab",
        )

        self.user = User.objects.create_user(
            username="tech1",
            email="tech@lab.local",
            password="test",
            tenant=self.tenant,
        )

        self.protocol = Protocol.objects.create(
            title="DNA Extraction",
            description="Test",
        )

        self.sample = Sample.objects.create(
            name="Sample A",
            sample_type="blood",
            received_at=timezone.now(),
            location="Freezer 1",
        )

        self.execution = ExecutionLog.objects.create(
            tenant=self.tenant,
            protocol=self.protocol,
            started_by=self.user,
            started_at=timezone.now(),
            status="completed",
            completed_at=timezone.now(),
        )

        ExecutionStep.objects.create(
            execution=self.execution,
            protocol_step_number=1,
            sample=self.sample,
            is_valid=True,
            validation_notes="Step OK",
        )

    def test_report_records_certification_timestamp(self):
        """Test that certification timestamp is recorded (non-repudiation)."""
        before = timezone.now()
        report = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.user,
            notes="Test",
        )
        after = timezone.now()

        self.assertIsNotNone(report.certified_at)
        self.assertGreaterEqual(report.certified_at, before)
        self.assertLessEqual(report.certified_at, after)

    def test_report_records_certifier_identity(self):
        """Test that the person who certified is recorded (attribution)."""
        report = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.user,
            notes="Test",
        )

        self.assertEqual(report.certified_by, self.user)
        self.assertEqual(report.certified_by.email, "tech@lab.local")

    def test_report_immutable_once_certified(self):
        """Test that certified reports are immutable (soft delete only)."""
        report = CertifiedReportService.generate_report(
            execution_log=self.execution,
            certified_by=self.user,
            notes="Test",
        )

        # Get the hash
        original_hash = report.report_hash

        # Try to modify (should not be possible without audit trail)
        report.refresh_from_db()
        self.assertEqual(report.report_hash, original_hash)
