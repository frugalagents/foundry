"""FastAPI application — Lambda-compatible via Mangum."""
from __future__ import annotations
import asyncio
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from api.routers import admin, architecture, customers, sessions, stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app = FastAPI(
    title="Platform Advisor API",
    version="1.0.0",
    description="Agentic AI Platform Advisory System",
    docs_url="/docs" if os.environ.get("ENV", "dev") != "prod" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router, prefix="/api/v1")
app.include_router(sessions.router,  prefix="/api/v1")
app.include_router(stream.router,    prefix="/api/v1")
app.include_router(admin.router,     prefix="/api/v1")
app.include_router(architecture.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Mangum adapter ─────────────────────────────────────────────────────────────
_mangum = Mangum(app, lifespan="off")


def handler(event, context):
    """Lambda entry point. Creates a fresh event loop (required for Python 3.10+)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return _mangum(event, context)
    finally:
        loop.close()
        asyncio.set_event_loop(None)
