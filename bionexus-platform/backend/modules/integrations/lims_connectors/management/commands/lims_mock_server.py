"""Unified mock server for every LIMS / QMS / ELN we integrate with.

A single HTTP server (default ``http://0.0.0.0:8001``) routes incoming
requests to the vendor whose ``url_prefix`` matches the path. The
registry is populated at app-load via each vendor's ``mock_routes``
module, so as long as a vendor is in INSTALLED_APPS its routes are
live.

Endpoints by vendor (default port 8001):
  Veeva       http://localhost:8001/veeva/api/v23.1/...
  Empower     http://localhost:8001/empower/v1.0/...
  LabWare     http://localhost:8001/labware/api/v1/...
  STARLIMS    http://localhost:8001/starlims/api/...
  Benchling   http://localhost:8001/benchling/v2/...
  Healthz     http://localhost:8001/healthz

The legacy single-vendor ``veeva_mock_server`` command is kept as a
thin wrapper for backward compatibility (see veeva/management/commands).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.integrations.base.mock_handler import (
    registered_vendors,
    serve,
)


class Command(BaseCommand):
    help = (
        "Run the unified LIMS mock server (Veeva + Empower + LabWare + "
        "STARLIMS + Benchling). Used for FL Basel demo + local dev."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=8001)

    def handle(self, *args, **options) -> None:
        host = options["host"]
        port = options["port"]

        vendors = registered_vendors()
        if not vendors:
            self.stdout.write(self.style.WARNING(
                "No vendors registered. Ensure modules.integrations.veeva and "
                "modules.integrations.lims_connectors are in INSTALLED_APPS."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Starting LIMS mock server with {len(vendors)} vendor(s):"
        ))
        for v in vendors:
            self.stdout.write(
                f"  - {v.vendor:<10} prefix={v.url_prefix}  "
                f"objects={list(v.object_routes.keys())}"
            )
        serve(host, port)
