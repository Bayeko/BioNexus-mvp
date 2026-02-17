"""Decorators for authentication and authorization in views.

Provides:
- @authenticate_required: Ensures request has valid JWT token
- @permission_required: Checks if user has specific permission
- @tenant_context: Injects tenant_id into request for isolation
"""

import functools
from typing import Callable, Optional

from rest_framework import status
from rest_framework.response import Response

from .jwt_service import JWTService


def authenticate_required(view_func: Callable) -> Callable:
    """Decorator to require JWT authentication on a view.

    Usage:
        @authenticate_required
        def my_view(request):
            user_context = request.auth_user
            ...
    """

    @functools.wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user_context = JWTService.extract_user_context(request)
        if not user_context:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Inject user context into request
        request.auth_user = user_context
        return view_func(self, request, *args, **kwargs)

    return wrapper


def permission_required(permission: str) -> Callable:
    """Decorator to check user has specific permission.

    Usage:
        @permission_required(Permission.SAMPLE_DELETE)
        def delete_sample(request, sample_id):
            ...
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            user_context = JWTService.extract_user_context(request)
            if not user_context:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if permission not in user_context.get("permissions", []):
                return Response(
                    {
                        "error": f"Permission denied. Required: {permission}",
                        "required_permission": permission,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            request.auth_user = user_context
            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def tenant_context(view_func: Callable) -> Callable:
    """Decorator to inject tenant_id from JWT into request.

    Ensures all operations are filtered by tenant for isolation.

    Usage:
        @tenant_context
        def list_samples(request):
            tenant_id = request.tenant_id
            # Repository will auto-filter by tenant
    """

    @functools.wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user_context = JWTService.extract_user_context(request)
        if user_context:
            request.tenant_id = user_context["tenant_id"]
            request.auth_user = user_context
        return view_func(self, request, *args, **kwargs)

    return wrapper
