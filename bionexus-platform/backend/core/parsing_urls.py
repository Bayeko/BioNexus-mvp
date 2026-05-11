from django.urls import path
from core.parsing_demo_views import (
    parsing_list,
    parsing_detail,
    parsing_upload,
    parsing_validate,
    parsing_reject,
)

urlpatterns = [
    path("", parsing_list, name="parsing-list"),
    path("upload/", parsing_upload, name="parsing-upload"),
    path("<int:pk>/", parsing_detail, name="parsing-detail"),
    path("<int:pk>/validate/", parsing_validate, name="parsing-validate"),
    path("<int:pk>/reject/", parsing_reject, name="parsing-reject"),
]

