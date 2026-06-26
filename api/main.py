import time
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from api.models import HealthResponse
from api.routes.auth import router as auth_router
from api.routes.sessions import router as sessions_router
from api.routes.analyse import router as analyse_router
from api.routes.dashboard import router as dashboard_router
from api.routes.action_plan import router as action_plan_router
from api.routes.report import router as report_router
from api.routes.export import router as export_router


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response


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
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ResponseTimeMiddleware)

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(analyse_router)
    app.include_router(dashboard_router)
    app.include_router(action_plan_router)
    app.include_router(report_router)
    app.include_router(export_router)

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health():
        return HealthResponse(
            status="ok",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            modules=["auth", "sessions", "analyse",
                     "dashboard", "action_plan", "report", "export"],
        )

    return app


app = create_app()
