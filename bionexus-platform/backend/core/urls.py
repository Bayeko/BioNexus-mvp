from django.urls import include, path
from rest_framework.routers import DefaultRouter

 codex/add-sample-model-and-crud-views
from modules.samples.views import SampleViewSet


router = DefaultRouter()
router.register(r"samples", SampleViewSet)


urlpatterns = [
    path("", include(router.urls)),

from modules.protocols.views import ProtocolViewSet

router = DefaultRouter()
router.register(r"protocols", ProtocolViewSet, basename="protocol")

urlpatterns = [
    path("api/", include(router.urls)),
 main
]
