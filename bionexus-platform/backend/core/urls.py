from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.samples.views import SampleViewSet
from modules.protocols.views import ProtocolViewSet
from core.connector_views import (
    list_connectors,
    get_connector,
    suggest_mappings,
    confirm_mappings,
    list_tenant_profiles,
    deactivate_profile,
)

router = DefaultRouter()
router.register(r"samples", SampleViewSet, basename="sample")
router.register(r"protocols", ProtocolViewSet, basename="protocol")

urlpatterns = [
    path("api/", include(router.urls)),
    # Plug-and-Parse Connector API endpoints
    path("api/connectors/", list_connectors, name="list-connectors"),
    path("api/connectors/<str:connector_id>/", get_connector, name="get-connector"),
    path("api/mappings/suggest/", suggest_mappings, name="suggest-mappings"),
    path("api/mappings/confirm/", confirm_mappings, name="confirm-mappings"),
    path("api/tenant-profiles/", list_tenant_profiles, name="list-tenant-profiles"),
    path("api/tenant-profiles/<int:profile_id>/deactivate/", deactivate_profile, name="deactivate-profile"),
]
