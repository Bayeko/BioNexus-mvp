"""Plug-and-Parse Hot-Plug Connector System.

This directory contains dynamically loadable connector plugins. Each file in
/connectors directory is a self-contained driver that can be loaded at runtime
without modifying core code.

Structure:
- /connectors/
  - hamilton_microlab.json     → Config for Hamilton Microlab STAR
  - tecan_freedom_evo.json     → Config for Tecan Freedom EVO
  - ... more connector configs

Each JSON file defines:
- connector_id: Unique identifier
- connector_type: SiLA 2 category (liquid_handler, plate_reader, etc.)
- fdl_descriptor: Feature Definition Language (output schema)
- pivot_mapping: How outputs map to our Pivot Model
"""

from .loader import ConnectorLoader, load_all_connectors

__all__ = ["ConnectorLoader", "load_all_connectors"]
