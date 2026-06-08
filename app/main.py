"""
Hogar — FastAPI application entry point.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from .config import settings
from .database import engine, init_db
from .errors import register_exception_handlers
from .logging_conf import configure_logging

logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    logger.info("startup", env=settings.APP_ENV)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hogar",
        version="0.1.0",
        description="Gestión doméstica para convivientes.",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"
        return {"status": "ok", "db": db_status, "env": settings.APP_ENV}

    @app.get("/api/health/live", tags=["meta"])
    async def liveness() -> dict:
        return {"status": "ok"}

    @app.get("/api/health/ready", tags=["meta"])
    async def readiness() -> dict:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    # TODO iter 2+: montar routers
    # from .routers import auth, invites, users, tasks, checklist, shopping, budget, roulette
    # app.include_router(auth.router, prefix="/api")
    # app.include_router(invites.router, prefix="/api")
    # app.include_router(users.router, prefix="/api")
    # app.include_router(tasks.router, prefix="/api")
    # app.include_router(checklist.router, prefix="/api")
    # app.include_router(shopping.router, prefix="/api")
    # app.include_router(budget.router, prefix="/api")
    # app.include_router(roulette.router, prefix="/api")

    return app


app = create_app()
