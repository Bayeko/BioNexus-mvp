from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"log", views.VeevaPushLogViewSet, basename="veeva-pushlog")

urlpatterns = [
    path("status/", views.veeva_status, name="veeva-status"),
    # OAuth2 Authorization Code flow (only active when VEEVA_AUTH_FLOW=oauth2)
    path("oauth/authorize-url/", views.oauth_authorize_url, name="veeva-oauth-authorize-url"),
    path("oauth/callback/", views.oauth_callback, name="veeva-oauth-callback"),
    path("oauth/status/", views.oauth_status, name="veeva-oauth-status"),
    path("", include(router.urls)),
]
