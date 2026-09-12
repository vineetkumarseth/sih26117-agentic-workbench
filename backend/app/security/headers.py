from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Belt-and-braces HTTP headers. None of this replaces TLS — put this
    service behind HTTPS (a reverse proxy on the plant network is enough,
    see docs/SECURITY.md) — but it costs nothing and blocks a few classes
    of browser-side attacks (clickjacking, MIME sniffing, referrer leaks).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Conservative default CSP for the API responses themselves
        # (the frontend, served separately by Vite/nginx, sets its own).
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
