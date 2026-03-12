from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.audit_views import AuditLogViewSet
from modules.instruments.views import InstrumentViewSet
from modules.measurements.views import MeasurementViewSet
from modules.protocols.views import ProtocolViewSet
from modules.samples.views import SampleViewSet

router = DefaultRouter()
router.register(r"instruments", InstrumentViewSet, basename="instrument")
router.register(r"samples", SampleViewSet, basename="sample")
router.register(r"measurements", MeasurementViewSet, basename="measurement")
router.register(r"protocols", ProtocolViewSet, basename="protocol")
router.register(r"audit", AuditLogViewSet, basename="auditlog")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/persistence/", include("modules.persistence.urls")),
    path("api/parsing/", include("core.parsing_urls")),
]

