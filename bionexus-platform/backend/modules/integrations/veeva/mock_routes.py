"""Veeva routes for the unified LIMS mock server.

Registers Veeva's REST v23.1 surface with the shared mock-handler
registry so a single ``manage.py lims_mock_server`` command serves
Veeva alongside Empower / LabWare / STARLIMS / Benchling.

This module is imported from ``apps.py:ready`` so registration happens
once at app load.
"""

from modules.integrations.base.mock_handler import VendorMockSpec, register_vendor


register_vendor(VendorMockSpec(
    vendor="veeva",
    url_prefix="/veeva",
    object_routes={
        "/api/v23.1/vobjects/quality_event__v": "VVQE",
    },
    document_routes={
        "/api/v23.1/objects/documents": "VVDOC",
    },
    auth_routes=["/api/v23.1/auth"],
    response_envelope="flat",
))
