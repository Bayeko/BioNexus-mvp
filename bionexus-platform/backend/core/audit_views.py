"""Read-only API for the immutable audit trail.

21 CFR Part 11 requires that audit records cannot be modified or deleted.
This viewset enforces read-only access.
"""

from rest_framework import serializers, viewsets
from rest_framework.response import Response

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "entity_type",
            "entity_id",
            "operation",
            "timestamp",
            "user_id",
            "user_email",
            "changes",
            "snapshot_before",
            "snapshot_after",
            "signature",
            "previous_signature",
        ]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit trail endpoint.

    GET /api/audit/       — List all audit records (newest first)
    GET /api/audit/{id}/  — Get a single audit record

    Filters via query params:
      ?entity_type=Sample         — Filter by model name
      ?entity_id=42               — Filter by entity PK
      ?operation=CREATE           — Filter by operation type
      ?user_email=user@lab.com    — Filter by user
    """

    serializer_class = AuditLogSerializer
    http_method_names = ["get", "head", "options"]  # strictly read-only

    def get_queryset(self):
        qs = AuditLog.objects.all().order_by("-timestamp", "-id")

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        entity_id = self.request.query_params.get("entity_id")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)

        operation = self.request.query_params.get("operation")
        if operation:
            qs = qs.filter(operation=operation.upper())

        user_email = self.request.query_params.get("user_email")
        if user_email:
            qs = qs.filter(user_email=user_email)

        return qs
