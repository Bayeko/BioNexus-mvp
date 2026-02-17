from django.apps import AppConfig


class ProtocolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.protocols"
    label = "protocols"  # Simplified app_label for ForeignKey references
