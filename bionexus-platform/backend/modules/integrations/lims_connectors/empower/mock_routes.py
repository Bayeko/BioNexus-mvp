from modules.integrations.base.mock_handler import VendorMockSpec, register_vendor


register_vendor(VendorMockSpec(
    vendor="empower",
    url_prefix="/empower",
    object_routes={
        "/v1.0/sample-results": "EMPRES",
    },
    auth_routes=["/v1.0/auth"],
    response_envelope="flat",
))
