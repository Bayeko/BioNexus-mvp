from django.apps import AppConfig


class VeevaIntegrationConfig(AppConfig):
    """Veeva Vault QMS integration (LBN-INT-VEEVA-001).

    Operates in one of four modes via VEEVA_MODE env var:
      - disabled : no-op, no network calls (production default)
      - mock     : pushes to a local mock Vault server (FL Basel demo path)
      - sandbox  : pushes to a real Veeva Vault sandbox (post partner-program approval)
      - prod     : pushes to a production Vault tenant (requires VEEVA_PROD_CONFIRMED=true)

    Per LBN-INT-VEEVA-001 spec v0.1, v1 is push-only (no Veeva-to-LBN pull).
    """

    name = "modules.integrations.veeva"
    label = "integrations_veeva"
    verbose_name = "Veeva Vault Integration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Wire post_save(Measurement) → service.push_measurement when enabled.
        from . import signals  # noqa: F401
        # Register Veeva's mock-server routes for the unified mock command.
        from . import mock_routes  # noqa: F401
