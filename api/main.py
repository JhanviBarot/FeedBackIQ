import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.models import HealthResponse
from api.routes.auth import router as auth_router
from api.routes.sessions import router as sessions_router
from api.routes.analyse import router as analyse_router
from api.routes.dashboard import router as dashboard_router
from api.routes.clusters import router as clusters_router
from api.routes.action_plan import router as action_plan_router
from api.routes.report import router as report_router
from api.routes.export import router as export_router
from api.routes.trends import router as trends_router
from api.routes.benchmarks import router as benchmarks_router
from api.routes.webhooks import router as webhooks_router

from api.middleware.rate_limiter import limiter
from api.middleware.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from core.config_validator import validate_config
from core.logger import logger
from core.rag.knowledge_base import initialise_knowledge_base


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        result = validate_config()
        logger.info(
            "FeedbackIQ starting",
            extra={
                "config_status": result["status"],
                "warnings": result["warnings"],
            },
        )
    except EnvironmentError as exc:
        logger.error(str(exc))
        raise

    try:
        loop = asyncio.get_event_loop()
        kb_count = await loop.run_in_executor(None, initialise_knowledge_base)
        logger.info(f"Knowledge base ready: {kb_count} documents loaded")
    except Exception as exc:
        logger.warning(f"Knowledge base initialisation failed (non-fatal): {exc}")

    yield
    logger.info("FeedbackIQ shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FeedbackIQ API",
        description=(
            "Customer feedback intelligence platform API. "
            "Classify reviews, generate AI insights, download reports."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiter state
    app.state.limiter = limiter

    # Exception handlers (order matters: most specific first)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Middleware
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ResponseTimeMiddleware)

    # Routers
    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(analyse_router)
    app.include_router(dashboard_router)
    app.include_router(clusters_router)
    app.include_router(action_plan_router)
    app.include_router(report_router)
    app.include_router(export_router)
    app.include_router(trends_router)
    app.include_router(benchmarks_router)
    app.include_router(webhooks_router)

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health():
        return HealthResponse(
            status="ok",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            modules=[
                "auth", "sessions", "analyse", "dashboard",
                "clusters", "action_plan", "report", "export", "trends",
                "benchmarks", "webhooks", "rag",
            ],
        )

    return app


app = create_app()
