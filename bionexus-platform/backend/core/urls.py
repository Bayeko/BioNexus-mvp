from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.samples.views import SampleViewSet
from modules.protocols.views import ProtocolViewSet

router = DefaultRouter()
router.register(r"samples", SampleViewSet)
router.register(r"protocols", ProtocolViewSet, basename="protocol")

urlpatterns = [
    path("api/", include(router.urls)),
]
