"""Django management command to load connector definitions from /connectors directory.

Usage:
    python manage.py load_connectors
"""

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import Connector, ConnectorMapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load connector definitions from /connectors directory and sync to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--connectors-dir",
            type=str,
            default=None,
            help="Path to connectors directory (default: ./connectors)",
        )
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Rebuild connector mappings (delete and recreate)",
        )

    def handle(self, *args, **options):
        connectors_dir = Path(options.get("connectors_dir") or "./connectors")
        rebuild = options.get("rebuild", False)

        if not connectors_dir.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Connectors directory not found: {connectors_dir}"
                )
            )
            return

        # Find all JSON files
        json_files = list(connectors_dir.glob("*.json"))
        self.stdout.write(
            self.style.SUCCESS(f"Found {len(json_files)} connector config(s)")
        )

        loaded = 0
        for json_file in json_files:
            try:
                self._load_connector_file(json_file, rebuild)
                loaded += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Loaded {json_file.name}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Failed to load {json_file.name}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{loaded}/{len(json_files)} connectors loaded successfully"
            )
        )

    def _load_connector_file(self, json_file: Path, rebuild: bool = False) -> None:
        """Load a single JSON connector file."""
        with open(json_file, "r") as f:
            config = json.load(f)

        # Validate required fields
        required = ["connector_id", "connector_name", "connector_type"]
        for field in required:
            if field not in config:
                raise ValueError(
                    f"Connector config missing required field: {field}"
                )

        connector_id = config["connector_id"]

        # Create or update Connector
        connector, created = Connector.objects.get_or_create(
            connector_id=connector_id,
            defaults={
                "connector_name": config.get("connector_name"),
                "description": config.get("description", ""),
                "connector_type": config.get("connector_type"),
                "version": config.get("version", "1.0.0"),
                "status": config.get("status", Connector.ACTIVE),
                "fdl_descriptor": config.get("fdl_descriptor", {}),
                "pivot_model_mapping": config.get("pivot_model_mapping", {}),
            },
        )

        # If rebuild, delete old mappings
        if rebuild:
            ConnectorMapping.objects.filter(connector=connector).delete()

        # Create output field mappings from pivot_model_mapping
        pivot_mapping = config.get("pivot_model_mapping", {})
        for machine_field, pivot_field in pivot_mapping.items():
            ConnectorMapping.objects.get_or_create(
                connector=connector,
                field_name=machine_field,
                defaults={
                    "data_type": "string",  # Default, can be overridden in FDL
                    "is_required": False,
                    "pivot_field": pivot_field,
                },
            )
