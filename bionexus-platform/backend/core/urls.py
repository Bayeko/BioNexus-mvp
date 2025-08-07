from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.samples.views import SampleViewSet


router = DefaultRouter()
router.register(r"samples", SampleViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
