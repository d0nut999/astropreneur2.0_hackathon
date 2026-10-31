"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import settings
from .db import init_db
from .security_headers import SecurityHeadersMiddleware
from . import routes
from .routes import (  # noqa: F401  (import so routes.<name> is available)
    approvals, audit, auth, candidates, digest, emails, health, jobs, portal,
)


def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    # Initialize database
    init_db()

    # Create app
    app = FastAPI(
        title="HireGuard",
        description="AI recruiting assistant with human oversight",
        version="0.1.0",
    )

    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    # Register routers
    app.include_router(routes.health.router)
    app.include_router(routes.auth.router)
    app.include_router(routes.jobs.router)
    app.include_router(routes.candidates.router)
    app.include_router(routes.approvals.router)
    app.include_router(routes.digest.router)
    app.include_router(routes.audit.router)
    app.include_router(routes.portal.router)
    app.include_router(routes.emails.router)

    return app


app = create_app()
