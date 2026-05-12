"""Benchling API v2 HTTP client.

Benchling auth: API token in ``Authorization: Bearer`` (or Basic for
older tenants). We default to Bearer; ``BENCHLING_API_TOKEN`` from env.
"""

from __future__ import annotations

import os

from modules.integrations.base.client import HttpLimsClient, build_client


class BenchlingClient(HttpLimsClient):
    vendor = "benchling"
    object_path = "/benchling/v2/result-rows"

    def _auth_headers(self) -> dict:
        headers = super()._auth_headers()
        token = os.environ.get("BENCHLING_API_TOKEN", "")
        if token and self.mode != "mock":
            headers["Authorization"] = f"Bearer {token}"
        return headers


def build_benchling_client():
    return build_client("benchling", client_class=BenchlingClient)
