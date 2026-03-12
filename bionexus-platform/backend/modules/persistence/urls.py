"""URL routes for the persistence (WAL) module."""

from django.urls import path

from . import views

urlpatterns = [
    path("capture/", views.CaptureView.as_view(), name="persistence-capture"),
    path("ingest/", views.IngestView.as_view(), name="persistence-ingest"),
    path("pending/", views.PendingListView.as_view(), name="persistence-pending"),
]
