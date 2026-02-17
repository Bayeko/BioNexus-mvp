from django.apps import AppConfig


class SamplesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.samples"
    label = "samples"  # Simplified app_label for ForeignKey references
