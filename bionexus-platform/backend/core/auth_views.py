"""Authentication endpoints for login and logout."""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .jwt_service import JWTService


@api_view(["POST"])
def login_view(request):
    """Authenticate user and return JWT tokens.

    Request body:
        {
            "username": "john.doe",
            "password": "secret123",
            "tenant_slug": "lab-a"  # Optional, inferred from username if omitted
        }

    Response:
        {
            "access": "eyJ0eXAi...",
            "refresh": "eyJ0eXAi...",
            "user_id": 123,
            "tenant_id": 456,
            "username": "john.doe",
            "role": "lab_technician"
        }
    """
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username and password required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Authenticate user (Django's authenticate ensures tenant isolation)
    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {"error": "User account is inactive"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Generate tokens
    tokens = JWTService.generate_tokens(user)

    # Log successful authentication in audit trail
    from .audit import AuditTrail

    AuditTrail.record(
        entity_type="User",
        entity_id=user.id,
        operation="LOGIN",
        changes={
            "ip_address": {
                "before": user.last_login_ip,
                "after": JWTService._get_client_ip(request),
            }
        },
        snapshot_before={},
        snapshot_after={
            "username": user.username,
            "tenant_id": user.tenant_id,
        },
        user_id=user.id,
        user_email=user.email,
    )

    return Response(tokens, status=status.HTTP_200_OK)


@api_view(["POST"])
def logout_view(request):
    """Logout user and revoke tokens.

    In a production system, you'd:
    1. Add token to a revocation list (Redis blacklist)
    2. Invalidate refresh tokens
    3. Log the logout event
    """
    from .jwt_service import JWTService

    user_context = JWTService.extract_user_context(request)
    if not user_context:
        return Response(
            {"error": "Not authenticated"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Log logout
    from .audit import AuditTrail

    AuditTrail.record(
        entity_type="User",
        entity_id=user_context["user_id"],
        operation="LOGOUT",
        changes={},
        snapshot_before={},
        snapshot_after={"username": user_context["username"]},
        user_id=user_context["user_id"],
        user_email=user_context["email"],
    )

    return Response(
        {"message": "Logged out successfully"},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def refresh_token_view(request):
    """Refresh an access token using a valid refresh token.

    Request body:
        {
            "refresh": "eyJ0eXAi..."
        }

    Response:
        {
            "access": "eyJ0eXAi...",  # New access token
            "refresh": "eyJ0eXAi..."   # Optionally new refresh token (rotation)
        }
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"error": "Refresh token required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = JWTService.verify_token(refresh_token, token_type="refresh")
    if not payload:
        return Response(
            {"error": "Invalid or expired refresh token"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Fetch user and generate new tokens
    from .models import User

    try:
        user = User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    tokens = JWTService.generate_tokens(user)
    return Response(tokens, status=status.HTTP_200_OK)
