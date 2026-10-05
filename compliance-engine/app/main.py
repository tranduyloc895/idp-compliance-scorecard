"""
FastAPI application entrypoint.

Lifespan: khởi tạo DB, Redis, K8s client khi startup → cleanup khi shutdown.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — startup/shutdown logic.

    Startup:
      1. Init Database (PostgreSQL via asyncpg)
      2. Run Alembic migrations
      3. Init Redis cache
      4. Init Kubernetes client (in-cluster or kubeconfig)
      5. Init AI Recommender (nếu GEMINI_API_KEY có)

    Shutdown:
      - Close Redis connection
      - Close K8s client
    """
    logger.info("=== Compliance Engine starting up ===")

    # 1. Init Database
    from app.database import init_db, get_engine, Base
    init_db(settings.DATABASE_URL)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

    # 2. Init Redis
    from app.cache import ComplianceCache
    cache = ComplianceCache(
        redis_url=settings.REDIS_URL,
        ttl_scores=settings.CACHE_TTL_SCORES,
        ttl_findings=settings.CACHE_TTL_FINDINGS,
        ttl_ai_rec=settings.CACHE_TTL_AI_RECOMMENDATIONS,
    )
    await cache.connect()
    app.state.cache = cache
    logger.info("Redis cache connected")

    # 3. Init Kubernetes client
    k8s_client = await _init_k8s_client()
    app.state.k8s_client = k8s_client

    # 4. Init AI Recommender
    app.state.ai_recommender = _init_ai_recommender()

    logger.info("=== Compliance Engine started successfully ===")

    yield  # App is running

    # ---- Shutdown ----
    logger.info("=== Compliance Engine shutting down ===")
    await cache.close()

    if k8s_client:
        await k8s_client.close()
        logger.info("Kubernetes client closed")

    await engine.dispose()
    logger.info("Database engine disposed")


async def _init_k8s_client():
    """Init K8s client: in-cluster → kubeconfig fallback."""
    try:
        from kubernetes_asyncio import client, config

        if settings.K8S_IN_CLUSTER:
            await config.load_incluster_config()
            logger.info("Kubernetes: in-cluster config loaded")
        elif settings.KUBECONFIG:
            await config.load_kube_config(config_file=settings.KUBECONFIG)
            logger.info("Kubernetes: kubeconfig loaded from %s", settings.KUBECONFIG)
        else:
            await config.load_kube_config()
            logger.info("Kubernetes: default kubeconfig loaded")

        k8s_client = client.ApiClient()
        logger.info("Kubernetes client initialized")
        return k8s_client

    except Exception as e:
        logger.warning(
            "Kubernetes client init failed (OK for local dev without cluster): %s", e
        )
        return None


def _init_ai_recommender() -> Optional[object]:
    """Init Gemini AI recommender nếu có API key."""
    if not settings.GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY not set — AI recommendations disabled. "
            "Set GEMINI_API_KEY to enable."
        )
        return None

    from app.recommender.ai_recommender import AIRecommender
    rec = AIRecommender(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    logger.info("AI Recommender initialized: model=%s", settings.GEMINI_MODEL)
    return rec


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Compliance Engine API",
    description=(
        "Continuous Compliance Scorecard Framework for Kubernetes. "
        "Aggregates findings from Kyverno, Trivy, kube-bench → weighted score → AI recommendations."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — allow Backstage frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production to Backstage URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

from app.api.routes.health import router as health_router
from app.api.routes.scan import router as scan_router
from app.api.routes.scores import router as scores_router
from app.api.routes.findings import router as findings_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.ai_analysis import router as ai_analysis_router

app.include_router(health_router)                              # /health
app.include_router(scan_router, prefix="/api/v1")             # /api/v1/scans
app.include_router(scores_router, prefix="/api/v1")           # /api/v1/scores
app.include_router(findings_router, prefix="/api/v1")         # /api/v1/findings
app.include_router(recommendations_router, prefix="/api/v1")  # /api/v1/findings/{id}/recommendation
app.include_router(ai_analysis_router, prefix="/api/v1")      # /api/v1/ai/*


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
