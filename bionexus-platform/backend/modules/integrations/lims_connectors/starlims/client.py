from __future__ import annotations

import os

from modules.integrations.base.client import HttpLimsClient, build_client


class StarlimsClient(HttpLimsClient):
    vendor = "starlims"
    object_path = "/starlims/api/test-results"

    def _auth_headers(self) -> dict:
        headers = super()._auth_headers()
        api_key = os.environ.get("STARLIMS_API_KEY", "")
        if api_key and self.mode != "mock":
            headers["X-Api-Key"] = api_key
        return headers


def build_starlims_client():
    return build_client("starlims", client_class=StarlimsClient)
