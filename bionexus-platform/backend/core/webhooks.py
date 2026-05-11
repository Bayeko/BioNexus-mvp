"""Webhook system for BioNexus event notifications.

Allows external systems (LIMS, ERP, etc.) to subscribe to BioNexus events
and receive real-time HTTP POST notifications when data changes occur.

Supported events:
- measurement.created
- sample.created / sample.updated
- instrument.status_changed
- parsing.validated / parsing.rejected
- audit.integrity_check
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime

import requests
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class WebhookSubscription(models.Model):
    """A webhook endpoint registered by an external system."""

    EVENT_CHOICES = [
        ("measurement.created", "Measurement Created"),
        ("sample.created", "Sample Created"),
        ("sample.updated", "Sample Updated"),
        ("instrument.status_changed", "Instrument Status Changed"),
        ("parsing.validated", "Parsing Validated"),
        ("parsing.rejected", "Parsing Rejected"),
        ("audit.integrity_check", "Audit Integrity Check"),
        ("*", "All Events"),
    ]

    name = models.CharField(max_length=255, help_text="Human-readable name (e.g., 'LabWare LIMS')")
    url = models.URLField(help_text="HTTPS endpoint that receives POST notifications")
    events = models.JSONField(
        default=list,
        help_text='List of event types to subscribe to (e.g., ["measurement.created", "sample.created"])',
    )
    secret = models.CharField(
        max_length=255,
        help_text="Shared secret for HMAC-SHA256 signature verification",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Delivery tracking
    last_delivery_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)

    class Meta:
        app_label = "core"

    def __str__(self):
        return f"{self.name} → {self.url}"


class WebhookDelivery(models.Model):
    """Log of every webhook delivery attempt."""

    subscription = models.ForeignKey(
        WebhookSubscription,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ["-delivered_at"]

    def __str__(self):
        status = "OK" if self.success else "FAIL"
        return f"[{status}] {self.event_type} → {self.subscription.name}"


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def dispatch_webhook(event_type: str, data: dict):
    """Send webhook notifications to all matching subscribers.

    Called from Django signals or view logic when events occur.
    """
    subscriptions = WebhookSubscription.objects.filter(is_active=True)

    for sub in subscriptions:
        # Check if subscription matches this event
        if "*" not in sub.events and event_type not in sub.events:
            continue

        payload = {
            "event": event_type,
            "timestamp": timezone.now().isoformat(),
            "data": data,
        }
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")
        signature = _sign_payload(payload_bytes, sub.secret)

        headers = {
            "Content-Type": "application/json",
            "X-BioNexus-Event": event_type,
            "X-BioNexus-Signature": f"sha256={signature}",
            "User-Agent": "BioNexus-Webhook/1.0",
        }

        delivery = WebhookDelivery(
            subscription=sub,
            event_type=event_type,
            payload=payload,
        )

        try:
            resp = requests.post(
                sub.url,
                data=payload_bytes,
                headers=headers,
                timeout=10,
            )
            delivery.status_code = resp.status_code
            delivery.response_body = resp.text[:1000]
            delivery.success = 200 <= resp.status_code < 300

            if delivery.success:
                sub.failure_count = 0
            else:
                sub.failure_count += 1

        except requests.RequestException as e:
            delivery.error = str(e)[:500]
            delivery.success = False
            sub.failure_count += 1
            logger.warning("Webhook delivery failed for %s: %s", sub.name, e)

        delivery.save()

        sub.last_delivery_at = timezone.now()
        sub.last_status_code = delivery.status_code
        # Auto-disable after 10 consecutive failures
        if sub.failure_count >= 10:
            sub.is_active = False
            logger.error("Webhook %s disabled after 10 consecutive failures", sub.name)
        sub.save(update_fields=["last_delivery_at", "last_status_code", "failure_count", "is_active"])
