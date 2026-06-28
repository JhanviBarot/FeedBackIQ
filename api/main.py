import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
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
    app.include_router(action_plan_router)
    app.include_router(report_router)
    app.include_router(export_router)
    app.include_router(trends_router)
    app.include_router(benchmarks_router)
    app.include_router(webhooks_router)

    @app.get("/api-docs", response_class=HTMLResponse, tags=["System"],
             include_in_schema=False)
    async def api_documentation():
        html = """<!DOCTYPE html>
<html>
<head>
    <title>FeedbackIQ API Documentation</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 900px;
               margin: 0 auto; padding: 40px 20px; color: #4A4A4A; }
        h1 { color: #0F6E56; border-bottom: 2px solid #0F6E56; padding-bottom: 12px; }
        h2 { color: #094D3C; margin-top: 40px; }
        h3 { color: #1A1A1A; }
        .endpoint { background: #F5F5F5; border-left: 4px solid #0F6E56;
                    padding: 12px 16px; margin: 12px 0; border-radius: 0 8px 8px 0; }
        .method { display: inline-block; padding: 2px 8px; border-radius: 4px;
                  font-weight: bold; font-size: 12px; margin-right: 8px; }
        .get    { background: #27AE60; color: white; }
        .post   { background: #0F6E56; color: white; }
        .put    { background: #E67E22; color: white; }
        .delete { background: #C0392B; color: white; }
        code { background: #E8F5F1; padding: 2px 6px; border-radius: 4px;
               font-family: monospace; }
        .note { background: #E8F5F1; border: 1px solid #0F6E56;
                padding: 12px; border-radius: 8px; margin: 16px 0; }
        a { color: #0F6E56; }
    </style>
</head>
<body>
    <h1>&#128202; FeedbackIQ API Documentation</h1>
    <div class="note">
        Base URL: <code>http://localhost:8000</code> (development) &nbsp;|&nbsp;
        Interactive docs: <a href="/docs">/docs</a> &nbsp;|&nbsp;
        OpenAPI spec: <a href="/openapi.json">/openapi.json</a>
    </div>

    <h2>Authentication</h2>
    <p>All protected endpoints require: <code>Authorization: Bearer {access_token}</code></p>

    <div class="endpoint">
        <span class="method post">POST</span><code>/auth/signup</code> — Create account
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/auth/login</code> — Login (form-data: username, password)
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/auth/refresh</code> — Refresh access token
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/auth/me</code> — Get current user &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/auth/profile</code> — Get saved company profile &#128274;
    </div>
    <div class="endpoint">
        <span class="method put">PUT</span><code>/auth/profile</code> — Save company profile &#128274;
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/auth/change-password</code> — Change password &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/auth/history</code> — Get analysis history &#128274;
    </div>

    <h2>Analysis</h2>
    <div class="endpoint">
        <span class="method post">POST</span><code>/sessions</code> — Create analysis session
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/sessions</code> — List user sessions &#128274;
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/analyse/text</code> — Analyse pasted text (form-data: session_id, raw_text)
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/analyse/file</code> — Analyse CSV/Excel file (multipart: session_id, file, column)
    </div>

    <h2>Results</h2>
    <div class="endpoint">
        <span class="method get">GET</span><code>/dashboard/{session_id}</code> — Full dashboard data &#128274;
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/action-plan/{session_id}</code> — Generate AI action plan &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/report/{session_id}</code> — Download PDF report &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/export/{session_id}</code> — Download CSV export &#128274;
    </div>

    <h2>Intelligence</h2>
    <div class="endpoint">
        <span class="method get">GET</span><code>/trends/me</code> — Sentiment trends across sessions &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/trends/{session_id}/context</code> — Trend context for session
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/benchmarks/{session_id}</code> — Industry benchmark comparison
    </div>

    <h2>Webhooks</h2>
    <div class="endpoint">
        <span class="method post">POST</span><code>/webhooks</code> — Register webhook &#128274;
    </div>
    <div class="endpoint">
        <span class="method get">GET</span><code>/webhooks</code> — Get webhook config &#128274;
    </div>
    <div class="endpoint">
        <span class="method delete">DELETE</span><code>/webhooks</code> — Delete webhook &#128274;
    </div>
    <div class="endpoint">
        <span class="method post">POST</span><code>/webhooks/test</code> — Send test webhook &#128274;
    </div>

    <h2>System</h2>
    <div class="endpoint">
        <span class="method get">GET</span><code>/health</code> — Health check
    </div>

    <p style="margin-top: 40px; color: #CCCCCC; font-size: 12px;">
        &#128274; = requires Authorization Bearer token &nbsp;|&nbsp;
        FeedbackIQ v1.0.0
    </p>
</body>
</html>"""
        return HTMLResponse(content=html)

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health():
        return HealthResponse(
            status="ok",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            modules=[
                "auth", "sessions", "analyse", "dashboard",
                "action_plan", "report", "export", "trends",
                "benchmarks", "webhooks",
            ],
        )

    return app


app = create_app()
