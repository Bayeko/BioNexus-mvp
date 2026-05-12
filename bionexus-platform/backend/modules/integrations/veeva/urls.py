from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"log", views.VeevaPushLogViewSet, basename="veeva-pushlog")

urlpatterns = [
    path("status/", views.veeva_status, name="veeva-status"),
    path("", include(router.urls)),
]
