from modules.integrations.base.mock_handler import VendorMockSpec, register_vendor


register_vendor(VendorMockSpec(
    vendor="benchling",
    url_prefix="/benchling",
    object_routes={
        "/v2/result-rows": "BCH",
    },
    auth_routes=["/v2/auth"],
    response_envelope="flat",
))
