from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.samples.views import SampleViewSet
from modules.protocols.views import ProtocolViewSet

router = DefaultRouter()
 codex/remove-trivial-backend/test_example.py
router.register(r"samples", SampleViewSet)
router.register(r"protocols", ProtocolViewSet, basename="protocol")

 codex/refactor-urls.py-for-routing
urlpatterns = [
    path("api/", include(router.urls)),

 codex/add-standard-settings-and-documentation
urlpatterns = [
    path("api/", include(router.urls)),

urlpatterns = [
    path("api/", include(router.urls)),

router.register(r'samples', SampleViewSet)
router.register(r'protocols', ProtocolViewSet, basename='protocol')

urlpatterns = [
    path('api/', include(router.urls)),
 main
 main
 main
]
