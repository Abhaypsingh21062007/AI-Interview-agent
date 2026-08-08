"""
Interview Agent — FastAPI Backend
Entry point. Wires together all routers and startup events.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging

from api.routes import router as api_router
from api.health import router as health_router
from api.demo_html import DEMO_HTML
from data.loader import CurriculumLoader, CandidateLoader

logger = logging.getLogger("main")

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

    # Serve interactive demo UI
    @app.get("/", response_class=HTMLResponse, tags=["Demo"])
    async def get_demo() -> HTMLResponse:
        return HTMLResponse(content=DEMO_HTML)

    # Register error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Request validation failed: {exc}")
        return JSONResponse(
            status_code=400,
            content={"detail": "Malformed request payload."}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error occurred in request lifecycle")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."}
        )

    # Startup: pre-load data into memory so loaders are warm
    @app.on_event("startup")
    async def _startup():
        CurriculumLoader.instance()
        CandidateLoader.instance()
        print("[startup] Curriculum and candidate data loaded OK")

    return app


app = create_app()
