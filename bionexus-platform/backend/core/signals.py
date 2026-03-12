"""Django signals for automatic audit trail logging.

Listens for post_save and pre_delete on registered models, and records
every mutation in the immutable AuditLog with SHA-256 signature chaining.

21 CFR Part 11 requires that all data changes are attributable, timestamped,
and tamper-proof.  These signals ensure no write path can bypass audit.
"""

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from core.audit import AuditTrail
from core.middleware import get_audit_user


# Models to auto-audit (imported lazily to avoid circular imports)
AUDITED_MODELS: list[str] = [
    "instruments.Instrument",
    "samples.Sample",
    "measurements.Measurement",
]


def _model_to_dict(instance) -> dict:
    """Serialise a model instance to a JSON-safe dict."""
    from decimal import Decimal

    result = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.attname)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        result[field.name] = value
    return result


def _is_audited(sender) -> bool:
    """Check if the model is in the audited list."""
    label = f"{sender._meta.app_label}.{sender.__name__}"
    return label in AUDITED_MODELS


@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Capture the old state before save for change detection."""
    if not _is_audited(sender):
        return
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._audit_old_state = _model_to_dict(old)
        except sender.DoesNotExist:
            instance._audit_old_state = {}
    else:
        instance._audit_old_state = {}


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Record CREATE or UPDATE in the audit trail after save."""
    if not _is_audited(sender):
        return

    user_id, user_email = get_audit_user()
    entity_type = sender.__name__
    snapshot_after = _model_to_dict(instance)

    if created:
        changes = {
            k: {"before": None, "after": v} for k, v in snapshot_after.items()
        }
        AuditTrail.record(
            entity_type=entity_type,
            entity_id=instance.pk,
            operation="CREATE",
            changes=changes,
            snapshot_before={},
            snapshot_after=snapshot_after,
            user_id=user_id,
            user_email=user_email,
        )
    else:
        old_state = getattr(instance, "_audit_old_state", {})
        changes = {}
        for field, new_val in snapshot_after.items():
            old_val = old_state.get(field)
            if old_val != new_val:
                changes[field] = {"before": old_val, "after": new_val}
        if changes:
            AuditTrail.record(
                entity_type=entity_type,
                entity_id=instance.pk,
                operation="UPDATE",
                changes=changes,
                snapshot_before=old_state,
                snapshot_after=snapshot_after,
                user_id=user_id,
                user_email=user_email,
            )


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    """Record DELETE in the audit trail before deletion."""
    if not _is_audited(sender):
        return

    user_id, user_email = get_audit_user()
    entity_type = sender.__name__
    snapshot_before = _model_to_dict(instance)

    AuditTrail.record(
        entity_type=entity_type,
        entity_id=instance.pk,
        operation="DELETE",
        changes={"deleted": {"before": False, "after": True}},
        snapshot_before=snapshot_before,
        snapshot_after={},
        user_id=user_id,
        user_email=user_email,
    )
