"""Protocol execution service - links intent (protocol) to action (results).

This service orchestrates:
1. Protocol execution start (creates ExecutionLog)
2. Step-by-step processing (creates ExecutionStep)
3. Result linking (ParsedData → ExecutionStep)
4. Technician validation (gates before data acceptance)

CRITICAL: Prevents orphaned data - every result MUST be linked
to a sample, step, and execution.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from django.utils import timezone

if TYPE_CHECKING:
    from modules.protocols.models import Protocol

from core.audit import AuditTrail
from core.models import (
    ExecutionLog,
    ExecutionStep,
    ParsedData,
    Equipment,
    Tenant,
    User,
)


class ProtocolExecutionService:
    """Orchestrates protocol execution with complete result linkage."""

    @staticmethod
    def start_execution(
        tenant: Tenant,
        protocol: "Protocol",
        user: User,
        equipment: Optional[Equipment] = None,
        source_file_id: Optional[int] = None,
    ) -> ExecutionLog:
        """Start a new protocol execution.

        This creates an ExecutionLog that will collect all steps
        and results for this protocol run.

        Args:
            tenant: Lab executing the protocol
            protocol: Which protocol is being run
            user: Technician starting execution
            equipment: Equipment being used (optional)
            source_file_id: RawFile ID if using machine output

        Returns:
            ExecutionLog (status=running)

        Audit Trail: Records execution start
        """
        from core.models import RawFile

        execution = ExecutionLog.objects.create(
            tenant=tenant,
            protocol=protocol,
            equipment=equipment,
            started_by=user,
            started_at=timezone.now(),
            status="running",
            source_file_id=source_file_id,
        )

        # Audit: Execution started
        AuditTrail.record(
            entity_type="ExecutionLog",
            entity_id=execution.id,
            operation="CREATE",
            changes={
                "status": {"before": None, "after": "running"},
                "protocol_id": {"before": None, "after": protocol.id},
            },
            snapshot_before={},
            snapshot_after={
                "id": execution.id,
                "protocol_id": protocol.id,
                "equipment_id": equipment.id if equipment else None,
                "started_at": execution.started_at.isoformat(),
            },
            user_id=user.id,
            user_email=user.email,
        )

        return execution

    @staticmethod
    def add_step_result(
        execution: ExecutionLog,
        step_number: int,
        sample_id: int,
        parsed_data: Optional[ParsedData] = None,
        validation_notes: str = "",
    ) -> ExecutionStep:
        """Link a result (ParsedData) to a protocol step.

        This is the critical linkage:
        - Sample: "Plate #5 - Patient ABC"
        - Step: "Step 3: Measure absorbance"
        - Result: ParsedData with measurements

        Args:
            execution: The ExecutionLog
            step_number: Step number in protocol
            sample_id: Which sample (ensures traceability)
            parsed_data: AI-extracted result (optional, can add later)
            validation_notes: Initial technician notes

        Returns:
            ExecutionStep

        Audit Trail: Records step completion
        """
        from modules.samples.models import Sample

        sample = Sample.objects.get(id=sample_id)

        step = ExecutionStep.objects.create(
            execution=execution,
            protocol_step_number=step_number,
            sample=sample,
            parsed_data=parsed_data,
            validation_notes=validation_notes,
        )

        # Audit: Step recorded
        AuditTrail.record(
            entity_type="ExecutionStep",
            entity_id=step.id,
            operation="CREATE",
            changes={
                "sample_id": {"before": None, "after": sample_id},
                "protocol_step": {"before": None, "after": step_number},
                "parsed_data_id": {
                    "before": None,
                    "after": parsed_data.id if parsed_data else None,
                },
            },
            snapshot_before={},
            snapshot_after={
                "id": step.id,
                "execution_id": execution.id,
                "sample_id": sample_id,
                "protocol_step": step_number,
                "parsed_data_id": parsed_data.id if parsed_data else None,
            },
            user_id=execution.started_by.id,
            user_email=execution.started_by.email,
        )

        return step

    @staticmethod
    def complete_execution(
        execution: ExecutionLog,
        user: User,
        notes: str = "",
    ) -> ExecutionLog:
        """Mark protocol execution as completed.

        Args:
            execution: ExecutionLog to complete
            user: Technician completing
            notes: Final notes about execution

        Returns:
            Updated ExecutionLog (status=completed)

        Audit Trail: Records completion
        """
        execution.completed_at = timezone.now()
        execution.status = "completed"
        execution.notes = notes
        execution.save(update_fields=["completed_at", "status", "notes"])

        # Audit: Execution completed
        AuditTrail.record(
            entity_type="ExecutionLog",
            entity_id=execution.id,
            operation="UPDATE",
            changes={
                "status": {"before": "running", "after": "completed"},
            },
            snapshot_before={"status": "running"},
            snapshot_after={
                "status": "completed",
                "completed_at": execution.completed_at.isoformat(),
            },
            user_id=user.id,
            user_email=user.email,
        )

        return execution

    @staticmethod
    def validate_step(
        step: ExecutionStep,
        validator: User,
        is_valid: bool = True,
        validation_notes: str = "",
    ) -> ExecutionStep:
        """Technician validates a step's result.

        This is the GATE: only validated steps are considered
        authoritative.

        Args:
            step: ExecutionStep to validate
            validator: Technician confirming
            is_valid: Does result match expectations?
            validation_notes: Why accepted/rejected

        Returns:
            Updated ExecutionStep

        Audit Trail: Records validation decision
        """
        step.is_valid = is_valid
        step.validation_notes = validation_notes
        step.save(update_fields=["is_valid", "validation_notes"])

        # Audit: Step validated
        AuditTrail.record(
            entity_type="ExecutionStep",
            entity_id=step.id,
            operation="UPDATE",
            changes={
                "is_valid": {"before": False, "after": is_valid},
            },
            snapshot_before={"is_valid": False},
            snapshot_after={
                "is_valid": is_valid,
                "validated_by": validator.username,
                "validation_notes": validation_notes,
            },
            user_id=validator.id,
            user_email=validator.email,
        )

        return step

    @staticmethod
    def get_unvalidated_steps(
        execution: ExecutionLog,
    ) -> list[ExecutionStep]:
        """Get all steps needing validation."""
        return ExecutionStep.objects.filter(
            execution=execution,
            is_valid=False,
        )

    @staticmethod
    def get_orphaned_parsed_data(tenant: Tenant) -> list[ParsedData]:
        """Find ParsedData not linked to any ExecutionStep.

        Orphaned data = results with no sample context (bad!)

        Returns:
            List of ParsedData without ExecutionStep
        """
        from django.db.models import Q

        return ParsedData.objects.filter(
            tenant=tenant,
            state=ParsedData.VALIDATED,  # Confirmed data
        ).exclude(
            execution_steps__isnull=False  # But not linked to execution
        )

    @staticmethod
    def link_parsed_data_to_step(
        step: ExecutionStep,
        parsed_data: ParsedData,
    ) -> ExecutionStep:
        """Retroactively link ParsedData to an ExecutionStep.

        Useful if result came in after step was created.

        Args:
            step: ExecutionStep to update
            parsed_data: ParsedData to link

        Returns:
            Updated ExecutionStep

        Audit Trail: Records linkage
        """
        old_parsed_id = step.parsed_data_id if step.parsed_data else None

        step.parsed_data = parsed_data
        step.save(update_fields=["parsed_data"])

        # Audit: LinkingRecord
        AuditTrail.record(
            entity_type="ExecutionStep",
            entity_id=step.id,
            operation="UPDATE",
            changes={
                "parsed_data_id": {
                    "before": old_parsed_id,
                    "after": parsed_data.id,
                },
            },
            snapshot_before={"parsed_data_id": old_parsed_id},
            snapshot_after={"parsed_data_id": parsed_data.id},
            user_id=step.execution.started_by.id,
            user_email=step.execution.started_by.email,
        )

        return step
