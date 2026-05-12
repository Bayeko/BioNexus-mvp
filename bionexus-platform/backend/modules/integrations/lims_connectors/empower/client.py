"""Waters Empower Web API HTTP client.

Empower auth is typically Basic Auth (corporate Empower account) or an
API key per the deployment. For sandbox/prod we read
``EMPOWER_API_KEY`` from the environment; mock mode skips auth.
"""

from __future__ import annotations

import os

from modules.integrations.base.client import HttpLimsClient, build_client


class EmpowerClient(HttpLimsClient):
    vendor = "empower"
    object_path = "/empower/v1.0/sample-results"

    def _auth_headers(self) -> dict:
        headers = super()._auth_headers()
        api_key = os.environ.get("EMPOWER_API_KEY", "")
        if api_key and self.mode != "mock":
            headers["X-API-Key"] = api_key
        return headers


def build_empower_client():
    return build_client("empower", client_class=EmpowerClient)
