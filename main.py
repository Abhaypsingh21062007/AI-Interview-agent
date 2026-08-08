"""
Interview Agent — FastAPI Backend
Entry point. Wires together all routers and startup events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.health import router as health_router
from data.loader import CurriculumLoader, CandidateLoader

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="The Interview Agent",
        description=(
            "AI-powered technical interview system for graduates of a "
            "31-day AI engineering cohort."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — open for local dev; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(api_router, prefix="/api", tags=["Interview"])

    # Startup: pre-load data into memory so loaders are warm
    @app.on_event("startup")
    async def _startup():
        CurriculumLoader.instance()
        CandidateLoader.instance()
        print("[startup] Curriculum and candidate data loaded OK")

    return app


app = create_app()
