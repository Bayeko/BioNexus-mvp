"""Request-context middleware for audit trail.

Stores the current request in thread-local storage so that Django signals
can access the authenticated user and IP address without explicit passing.
"""

import threading

_thread_locals = threading.local()


def get_current_request():
    """Return the current Django request from thread-local storage, or None."""
    return getattr(_thread_locals, "request", None)


def get_audit_user() -> tuple[int, str]:
    """Extract user_id and user_email from the current request.

    Falls back to system defaults when called outside a request context
    (e.g., management commands, migrations).
    """
    request = get_current_request()
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user.id, request.user.email or f"user-{request.user.id}@bionexus.local"
    return 0, "system@bionexus.local"


def get_client_ip() -> str:
    """Extract client IP from the current request."""
    request = get_current_request()
    if request:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
    return "system"


class AuditMiddleware:
    """Stores the current request in thread-local storage for signal access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.request = None
        return response
