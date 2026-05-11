from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from core.api_views import CertificationSigningViewSet, TOTPViewSet
from core.audit_views import AuditLogViewSet
from core.health_views import healthz
from core.export_views import (
    export_formats,
    export_measurements_csv,
    export_measurements_pdf,
    export_samples_csv,
    export_audit_csv,
)
from core.webhook_views import WebhookSubscriptionViewSet, WebhookEventListView
from modules.instruments.views import InstrumentViewSet, InstrumentConfigViewSet
from modules.measurements.views import MeasurementViewSet, MeasurementContextViewSet
from modules.protocols.views import ProtocolViewSet
from modules.samples.views import SampleViewSet

router = DefaultRouter()
router.register(r"instruments", InstrumentViewSet, basename="instrument")
router.register(r"instrument-configs", InstrumentConfigViewSet, basename="instrumentconfig")
router.register(r"samples", SampleViewSet, basename="sample")
router.register(r"measurements", MeasurementViewSet, basename="measurement")
router.register(r"measurement-contexts", MeasurementContextViewSet, basename="measurementcontext")
router.register(r"protocols", ProtocolViewSet, basename="protocol")
router.register(r"audit", AuditLogViewSet, basename="auditlog")
router.register(r"webhooks", WebhookSubscriptionViewSet, basename="webhook")
router.register(r"webhooks/events", WebhookEventListView, basename="webhook-events")
router.register(r"totp", TOTPViewSet, basename="totp")

certification_sign = CertificationSigningViewSet.as_view({"post": "create"})

urlpatterns = [
    # Liveness probe (UptimeRobot, GCP Cloud Monitoring, Sentry cron).
    # Kept at the root path so monitors don't need API prefix awareness.
    path("healthz", healthz, name="healthz"),
    path("healthz/", healthz),  # accept trailing slash for compatibility

    path("api/", include(router.urls)),
    path("api/reports/<int:pk>/sign/", certification_sign, name="report-sign"),
    path("api/persistence/", include("modules.persistence.urls")),
    path("api/parsing/", include("core.parsing_urls")),
    # Export endpoints
    path("api/export/", export_formats),
    path("api/export/measurements/csv/", export_measurements_csv),
    path("api/export/measurements/pdf/", export_measurements_pdf),
    path("api/export/samples/csv/", export_samples_csv),
    path("api/export/audit/csv/", export_audit_csv),
    # API Documentation (Swagger UI)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

