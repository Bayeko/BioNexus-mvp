from modules.integrations.base.mock_handler import VendorMockSpec, register_vendor


register_vendor(VendorMockSpec(
    vendor="labware",
    url_prefix="/labware",
    object_routes={
        "/api/v1/results": "LWRES",
    },
    auth_routes=["/api/v1/auth"],
    response_envelope="flat",
))
