from rest_framework import serializers

from .models import IntegrationPushLog


class IntegrationPushLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationPushLog
        fields = [
            "id",
            "target_object_type",
            "source_measurement_id",
            "source_report_id",
            "payload_hash",
            "target_object_id",
            "http_status",
            "last_error",
            "attempts",
            "status",
            "mode",
            "created_at",
            "last_attempt_at",
            "succeeded_at",
        ]
        read_only_fields = fields
