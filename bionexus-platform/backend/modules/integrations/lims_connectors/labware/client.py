"""LabWare LIMS REST HTTP client.

LabWare auth: API key in ``Authorization`` header for v2; session token
for older deployments. We default to API key for simplicity.
"""

from __future__ import annotations

import os

from modules.integrations.base.client import HttpLimsClient, build_client


class LabWareClient(HttpLimsClient):
    vendor = "labware"
    object_path = "/labware/api/v1/results"

    def _auth_headers(self) -> dict:
        headers = super()._auth_headers()
        api_key = os.environ.get("LABWARE_API_KEY", "")
        if api_key and self.mode != "mock":
            headers["Authorization"] = f"ApiKey {api_key}"
        return headers


def build_labware_client():
    return build_client("labware", client_class=LabWareClient)
