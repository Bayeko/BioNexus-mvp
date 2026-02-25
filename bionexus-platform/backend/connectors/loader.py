"""Hot-Plug Connector Loader - Dynamically load connectors from /connectors directory.

This loader scans the /connectors directory at startup and registers any
JSON connector configs without touching the core code.

Design: Remove the need to modify core/ app to add a new machine type.
Simply drop a JSON file in /connectors and it's loaded at runtime.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConnectorLoader:
    """Load connector definitions from JSON files in /connectors directory."""

    def __init__(self, connectors_dir: str = None):
        """Initialize loader.

        Args:
            connectors_dir: Path to connectors directory. If None, uses ./connectors
        """
        if connectors_dir is None:
            connectors_dir = Path(__file__).parent
        self.connectors_dir = Path(connectors_dir)
        self.loaded_connectors = {}

    def load_all(self) -> dict:
        """Scan /connectors directory and load all JSON connector configs.

        Returns:
            Dict of loaded connectors: {connector_id: config_dict}
        """
        if not self.connectors_dir.exists():
            logger.warning(
                f"Connectors directory not found: {self.connectors_dir}"
            )
            return {}

        json_files = self.connectors_dir.glob("*.json")
        for json_file in json_files:
            try:
                self._load_connector_file(json_file)
            except Exception as e:
                logger.error(f"Failed to load connector {json_file.name}: {e}")

        logger.info(
            f"Loaded {len(self.loaded_connectors)} connectors from "
            f"{self.connectors_dir}"
        )
        return self.loaded_connectors

    def _load_connector_file(self, json_file: Path) -> None:
        """Load a single JSON connector file.

        Args:
            json_file: Path to .json file
        """
        with open(json_file, "r") as f:
            config = json.load(f)

        # Validate required fields
        required_fields = ["connector_id", "connector_name", "connector_type"]
        for field in required_fields:
            if field not in config:
                raise ValueError(
                    f"Connector config missing required field: {field}"
                )

        connector_id = config["connector_id"]
        self.loaded_connectors[connector_id] = config
        logger.debug(f"Loaded connector: {connector_id} ({config['connector_name']})")

    def sync_to_database(self):
        """Sync loaded connectors to Django database (core.Connector model).

        This is called during Django startup to ensure all file-based
        connectors are registered in the database.
        """
        from django.apps import apps

        # Lazy import to avoid circular dependencies
        Connector = apps.get_model("core", "Connector")

        for connector_id, config in self.loaded_connectors.items():
            try:
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
                action = "created" if created else "updated"
                logger.debug(f"Connector {connector_id} {action} in database")
            except Exception as e:
                logger.error(
                    f"Failed to sync connector {connector_id} to database: {e}"
                )


def load_all_connectors(connectors_dir: str = None) -> dict:
    """Convenience function to load all connectors from directory.

    Args:
        connectors_dir: Path to connectors directory

    Returns:
        Dict of loaded connectors
    """
    loader = ConnectorLoader(connectors_dir)
    return loader.load_all()
