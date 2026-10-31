"""Security headers middleware."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


DOCS_PATHS = {"/docs", "/redoc", "/docs/oauth2-redirect"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Content Security Policy
        if request.url.path in DOCS_PATHS:
            # The API docs page (/docs) loads its scripts from a CDN, so allow only that here.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
                "connect-src 'self'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # No XSS filtering (modern browsers handle this)
        response.headers["X-XSS-Protection"] = "0"

        return response
