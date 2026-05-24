from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.rate_limit import limiter
from app.routers import audit, auth, brain, commands, devices, files, google, hermes, pairing

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title="Hermes API", version="1.0.0")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    origins = [o.strip().rstrip("/") for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    api = "/api/v1"
    app.include_router(auth.router, prefix=api)
    app.include_router(pairing.router, prefix=api)
    app.include_router(devices.router, prefix=api)
    app.include_router(commands.router, prefix=api)
    app.include_router(brain.router, prefix=api)
    app.include_router(files.router, prefix=api)
    app.include_router(google.router, prefix=api)
    app.include_router(hermes.router, prefix=api)
    app.include_router(audit.router, prefix=api)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()
