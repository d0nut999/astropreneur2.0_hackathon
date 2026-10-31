"""FastAPI application factory."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from .auth import require_user
from .config import settings
from .db import init_db
from .security_headers import SecurityHeadersMiddleware
from . import routes
from .routes import (  # noqa: F401  (import so routes.<name> is available)
    approvals, audit, auth, calendar, candidates, digest, emails, health, jobs, portal, schedule, system,
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
    # Public: health, login, candidate portal (protected by its own one-time token)
    app.include_router(routes.health.router)
    app.include_router(routes.auth.router)
    app.include_router(routes.portal.router)
    app.include_router(routes.schedule.router)  # public: candidate picks an interview time
    # HR only: every route below requires a logged-in user (+ CSRF header for changes)
    logged_in = [Depends(require_user)]
    app.include_router(routes.jobs.router, dependencies=logged_in)
    app.include_router(routes.candidates.router, dependencies=logged_in)
    app.include_router(routes.approvals.router, dependencies=logged_in)
    app.include_router(routes.digest.router, dependencies=logged_in)
    app.include_router(routes.audit.router, dependencies=logged_in)
    app.include_router(routes.emails.router, dependencies=logged_in)
    app.include_router(routes.system.router, dependencies=logged_in)
    app.include_router(routes.calendar.router, dependencies=logged_in)

    return app


app = create_app()
