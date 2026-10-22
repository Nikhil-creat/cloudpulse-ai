import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

MAX_BODY = 1_000_000


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        resp = await call_next(request)
        h = resp.headers
        h["X-Request-ID"] = rid
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
            h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return resp
