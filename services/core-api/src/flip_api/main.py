"""
FLIP Core API — FastAPI + Strawberry GraphQL Federation
Entry point: FastAPI application with lifespan management.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from flip_api.config import settings
from flip_api.database import create_engine_and_pool, close_engine
from flip_api.events.nats_client import NATSClient
from flip_api.graphql.schema import graphql_app

# --- Structured Logging Setup ---
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger(__name__)

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    "flip_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "flip_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

# --- Shared NATS Client ---
nats_client: NATSClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    global nats_client  # noqa: PLW0603

    logger.info("FLIP API starting up", env=settings.FLIP_ENV, version=settings.API_VERSION)

    # 1. Initialize database connection pool
    await create_engine_and_pool()
    logger.info("Database pool initialized")

    # 2. Connect to NATS JetStream
    nats_client = NATSClient(nats_url=settings.NATS_URL)
    await nats_client.connect()
    await nats_client.ensure_streams()
    logger.info("NATS JetStream connected", url=settings.NATS_URL)

    # 3. Start pg_notify → NATS bridge (background task)
    pg_bridge_task = asyncio.create_task(
        nats_client.listen_pg_notify(settings.DATABASE_URL),
        name="pg_nats_bridge",
    )
    logger.info("pg_notify NATS bridge started")

    # 4. Yield — application is running
    yield

    # Shutdown
    pg_bridge_task.cancel()
    try:
        await pg_bridge_task
    except asyncio.CancelledError:
        pass
    logger.info("pg_notify NATS bridge stopped")

    if nats_client:
        await nats_client.close()
        logger.info("NATS disconnected")
    await close_engine()
    logger.info("Database pool closed")
    logger.info("FLIP API shut down cleanly")


# --- FastAPI App ---
app = FastAPI(
    title="FLIP Core API",
    description="Farm Lifecycle Intelligence Platform — FastAPI + Strawberry GraphQL",
    version=settings.API_VERSION,
    docs_url="/docs" if settings.FLIP_ENV != "production" else None,
    redoc_url="/redoc" if settings.FLIP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.FLIP_ENV != "production" else None,
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Prometheus Metrics Middleware ---
@app.middleware("http")
async def metrics_middleware(request: Request, call_next: object) -> Response:
    start = time.perf_counter()
    response = await call_next(request)  # type: ignore[operator]
    duration = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)
    return response


# --- Health Check ---
@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.API_VERSION,
        "env": settings.FLIP_ENV,
    }


@app.get("/health/ready", tags=["Health"])
async def health_ready() -> dict:
    return {"status": "ready"}


# --- Prometheus Metrics Endpoint ---
@app.get("/metrics", tags=["Observability"])
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# --- Middlewares ---
from flip_api.middleware.auth_middleware import AuthMiddleware

app.add_middleware(AuthMiddleware)

# --- REST Routers ---
from flip_api.routers import (
    sensors_router,
    farms_router,
    advisories_router,
    disaster_router,
    copilot_router,
    auth_router,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(sensors_router, prefix="/api/v1")
app.include_router(farms_router, prefix="/api/v1")
app.include_router(advisories_router, prefix="/api/v1")
app.include_router(disaster_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")

# --- GraphQL (Strawberry) ---
app.include_router(graphql_app, prefix="/graphql")

# --- WebSocket: Live Sensor Stream ---
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/farms/{farm_id}/sensors")
async def ws_sensor_stream(websocket: WebSocket, farm_id: str) -> None:
    """Proxy NATS farm.<farm_id>.sensor.processed → WebSocket."""
    await websocket.accept()
    logger.info("ws_sensor_stream_connect", farm_id=farm_id)

    if nats_client is None:
        await websocket.send_json({"error": "NATS not available"})
        await websocket.close()
        return

    sub = None
    try:
        sub = await nats_client.subscribe(
            subject=f"farm.{farm_id}.sensor.processed",
            durable=None,  # Push subscriber (ephemeral for WS)
        )
        async for msg in sub.messages:
            if msg is None:
                break
            await websocket.send_bytes(msg.data)
    except WebSocketDisconnect:
        logger.info("ws_sensor_stream_disconnect", farm_id=farm_id)
    finally:
        if sub:
            try:
                await sub.unsubscribe()
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "flip_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.FLIP_ENV == "local",
        log_level="debug" if settings.FLIP_ENV == "local" else "info",
    )
