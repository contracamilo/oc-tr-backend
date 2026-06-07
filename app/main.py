"""
Hogar — FastAPI application entry point.

ESQUELETO — iter 1.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hogar",
        version="0.1.0",
        description="Gestión doméstica para convivientes.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "env": settings.APP_ENV}

    # TODO iter 2+: montar routers reales
    # from .routers import users, tasks, checklist, shopping, budget, roulette
    # app.include_router(users.router, prefix="/api")
    # app.include_router(tasks.router, prefix="/api")
    # ...

    # TODO iter 2+ (opcional): servir frontend
    # from fastapi.staticfiles import StaticFiles
    # app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

    return app


app = create_app()
