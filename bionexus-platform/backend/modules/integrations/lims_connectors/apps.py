from django.apps import AppConfig


class LimsConnectorsConfig(AppConfig):
    """Umbrella app that hosts the Empower / LabWare / STARLIMS / Benchling
    connectors. Each is a thin submodule; all share
    ``modules/integrations/base/`` for the HTTP / retry / signing
    primitives and the ``modules/integrations/veeva/IntegrationPushLog``
    model for audit-trail persistence.
    """

    name = "modules.integrations.lims_connectors"
    label = "lims_connectors"
    verbose_name = "LIMS Connectors (Empower / LabWare / STARLIMS / Benchling)"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Register each vendor's signal handlers + mock routes.
        from .empower import signals as _empower_signals  # noqa: F401
        from .labware import signals as _labware_signals  # noqa: F401
        from .starlims import signals as _starlims_signals  # noqa: F401
        from .benchling import signals as _benchling_signals  # noqa: F401
        from .empower import mock_routes as _empower_mock  # noqa: F401
        from .labware import mock_routes as _labware_mock  # noqa: F401
        from .starlims import mock_routes as _starlims_mock  # noqa: F401
        from .benchling import mock_routes as _benchling_mock  # noqa: F401
