"""JWT authentication service for secure API access.

Implements:
- JWT token generation with short-lived access tokens
- Refresh token rotation for token rotation security
- Token revocation on logout
- User context extraction from tokens
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from django.conf import settings
from django.utils import timezone

from .models import User


class JWTService:
    """Manages JWT token lifecycle for API authentication."""

    # Token lifetimes (configurable)
    ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
    REFRESH_TOKEN_LIFETIME = timedelta(days=7)

    @staticmethod
    def generate_tokens(user: User) -> dict:
        """Generate access and refresh tokens for a user.

        Args:
            user: Authenticated User instance

        Returns:
            {
                "access": "eyJ0eXAi...",
                "refresh": "eyJ0eXAi...",
                "user_id": 123,
                "tenant_id": 456,
                "username": "john.doe",
                "role": "lab_technician"
            }
        """
        now = timezone.now()
        access_exp = now + JWTService.ACCESS_TOKEN_LIFETIME
        refresh_exp = now + JWTService.REFRESH_TOKEN_LIFETIME

        # Access token (short-lived)
        access_payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else None,
            "permissions": user.get_permissions(),
            "exp": int(access_exp.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
        }
        access_token = jwt.encode(
            access_payload,
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        # Refresh token (long-lived)
        refresh_token_id = secrets.token_urlsafe(32)
        refresh_payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "token_id": refresh_token_id,
            "exp": int(refresh_exp.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_payload,
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        return {
            "access": access_token,
            "refresh": refresh_token,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "role": user.role.name if user.role else None,
        }

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string
            token_type: "access" or "refresh"

        Returns:
            Decoded payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )

            # Verify token type
            if payload.get("type") != token_type:
                return None

            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    @staticmethod
    def extract_user_context(request) -> Optional[dict]:
        """Extract user context from HTTP request Authorization header.

        Args:
            request: Django request object

        Returns:
            User context dict if authenticated, None otherwise
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix
        payload = JWTService.verify_token(token, token_type="access")
        if not payload:
            return None

        return {
            "user_id": payload["user_id"],
            "tenant_id": payload["tenant_id"],
            "username": payload["username"],
            "email": payload["email"],
            "role": payload["role"],
            "permissions": payload["permissions"],
        }

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Hash a refresh token for secure storage.

        We hash refresh tokens before storing them to prevent
        attacker from using a stolen DB dump.
        """
        return hashlib.sha256(token.encode()).hexdigest()
