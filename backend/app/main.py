import uuid
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import get_settings
from backend.app.api.router import api_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("trackmeld")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting TrackMeld API (%s environment)", settings.ENVIRONMENT)
    yield
    logger.info("Stopping TrackMeld API")


app = FastAPI(
    title="TrackMeld API",
    description="Railway maintenance possession planning and decision-support system backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Explicit CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Attach unique request_id to each incoming request and response headers."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
}


@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    """Attach standard HTTP security headers to every response.

    HSTS is intentionally omitted: this prototype runs on plain HTTP in
    development. Add HSTS only when served over verified HTTPS in production.
    CSP allows 'unsafe-inline' for Next.js SSR compatibility; tighten in
    production once nonce-based inline scripts are implemented.
    """
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers[k] = v
    return response


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Normalize HTTP exceptions into consistent TrackMeld error payload."""
    if exc.status_code >= 500:
        logger.error(
            "Server error HTTP %s on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )

    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        if exc.status_code >= 500 and (settings.is_production or settings.ENVIRONMENT != "development"):
            message = "An unexpected internal server error occurred."
        else:
            message = str(exc.detail)
        payload = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
            }
        }
    headers = dict(SECURITY_HEADERS)
    if getattr(exc, "headers", None):
        headers.update(exc.headers)
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload structure.",
                "details": exc.errors(),
            }
        },
        headers=SECURITY_HEADERS,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, log the stack trace, and return a clean JSON payload."""
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
            }
        },
        headers=SECURITY_HEADERS,
    )


# Mount routes
app.include_router(api_router)
