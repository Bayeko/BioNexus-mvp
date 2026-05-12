from modules.integrations.base.mock_handler import VendorMockSpec, register_vendor


register_vendor(VendorMockSpec(
    vendor="starlims",
    url_prefix="/starlims",
    object_routes={
        "/api/test-results": "SLTR",
    },
    auth_routes=["/api/auth"],
    response_envelope="flat",
))
