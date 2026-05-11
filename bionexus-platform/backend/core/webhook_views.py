"""API views for webhook subscription management."""

from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from .webhooks import WebhookSubscription, WebhookDelivery


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = [
            "id", "name", "url", "events", "secret", "is_active",
            "created_at", "updated_at",
            "last_delivery_at", "last_status_code", "failure_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_delivery_at", "last_status_code", "failure_count"]
        extra_kwargs = {"secret": {"write_only": True}}


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = [
            "id", "subscription", "event_type", "payload",
            "status_code", "success", "error", "delivered_at",
        ]


class WebhookSubscriptionViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for webhook subscriptions.

    GET    /api/webhooks/                — List all subscriptions
    POST   /api/webhooks/                — Register a new webhook
    GET    /api/webhooks/{id}/           — Get subscription details
    PUT    /api/webhooks/{id}/           — Update subscription
    DELETE /api/webhooks/{id}/           — Remove subscription
    GET    /api/webhooks/{id}/deliveries/ — View delivery history
    POST   /api/webhooks/{id}/test/      — Send a test event
    """

    serializer_class = WebhookSubscriptionSerializer
    queryset = WebhookSubscription.objects.all().order_by("-created_at")

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        """List recent deliveries for a webhook subscription."""
        subscription = self.get_object()
        deliveries = subscription.deliveries.all()[:50]
        serializer = WebhookDeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Send a test webhook event to verify the endpoint works."""
        from .webhooks import dispatch_webhook

        subscription = self.get_object()
        dispatch_webhook("test.ping", {
            "message": "This is a test event from BioNexus",
            "subscription_id": subscription.id,
            "subscription_name": subscription.name,
        })

        # Get the delivery result
        delivery = subscription.deliveries.first()
        if delivery:
            return Response({
                "status": "delivered" if delivery.success else "failed",
                "status_code": delivery.status_code,
                "error": delivery.error or None,
            })
        return Response({"status": "no_delivery"})


class WebhookEventListView(viewsets.ViewSet):
    """List available webhook event types.

    GET /api/webhooks/events/
    """

    def list(self, request):
        return Response({
            "events": [
                {"type": "measurement.created", "description": "A new measurement was recorded from an instrument"},
                {"type": "sample.created", "description": "A new sample was registered in the system"},
                {"type": "sample.updated", "description": "A sample status or field was updated"},
                {"type": "instrument.status_changed", "description": "An instrument went online, offline, or error"},
                {"type": "parsing.validated", "description": "A parsed file was validated by a human reviewer"},
                {"type": "parsing.rejected", "description": "A parsed file was rejected by a reviewer"},
                {"type": "audit.integrity_check", "description": "Audit chain integrity verification result"},
                {"type": "*", "description": "Subscribe to all events"},
            ],
            "headers": {
                "X-BioNexus-Event": "Event type that triggered this delivery",
                "X-BioNexus-Signature": "HMAC-SHA256 signature (sha256=<hex>) — verify with your shared secret",
            },
        })
