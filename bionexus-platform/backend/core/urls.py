from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.samples.views import SampleViewSet
from modules.protocols.views import ProtocolViewSet

 codex/refactor-urls-in-backend-core

router = DefaultRouter()
router.register(r"samples", SampleViewSet)
router.register(r"protocols", ProtocolViewSet, basename="protocol")

router = DefaultRouter()
router.register(r'samples', SampleViewSet)
router.register(r'protocols', ProtocolViewSet, basename='protocol')
 main


urlpatterns = [
 codex/refactor-urls-in-backend-core
    path("api/", include(router.urls)),

    path('api/', include(router.urls)),
 main
]

