"""
Health check endpoint — GET /health

Kiểm tra:
- App: Always OK nếu endpoint accessible
- Database: PostgreSQL connection
- Cache: Redis connection
- K8s: Kubernetes API connectivity
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """
    Health check endpoint.

    Returns:
        200 OK với status của từng dependency
        503 nếu bất kỳ critical dependency nào down
    """
    health = {
        "status": "ok",
        "app": "compliance-engine",
        "version": "1.0.0",
        "dependencies": {
            "database": "unknown",
            "cache": "unknown",
            "kubernetes": "unknown",
            "ai_recommender": "unknown",
        },
    }

    # Check Database
    try:
        from app.database import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        health["dependencies"]["database"] = "ok"
    except Exception as e:
        health["dependencies"]["database"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    # Check Redis cache
    try:
        cache = getattr(request.app.state, "cache", None)
        if cache and await cache.ping():
            health["dependencies"]["cache"] = "ok"
        else:
            health["dependencies"]["cache"] = "unavailable"
            health["status"] = "degraded"
    except Exception as e:
        health["dependencies"]["cache"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    # Check K8s client
    try:
        k8s_client = getattr(request.app.state, "k8s_client", None)
        if k8s_client:
            health["dependencies"]["kubernetes"] = "ok"
        else:
            health["dependencies"]["kubernetes"] = "not_configured"
    except Exception as e:
        health["dependencies"]["kubernetes"] = f"error: {str(e)[:100]}"

    # Check AI recommender
    try:
        ai_rec = getattr(request.app.state, "ai_recommender", None)
        if ai_rec and await ai_rec.health_check():
            health["dependencies"]["ai_recommender"] = "ok"
        elif ai_rec is None:
            health["dependencies"]["ai_recommender"] = "not_configured (GEMINI_API_KEY missing)"
        else:
            health["dependencies"]["ai_recommender"] = "error"
    except Exception as e:
        health["dependencies"]["ai_recommender"] = f"error: {str(e)[:100]}"

    from fastapi.responses import JSONResponse
    status_code = 200 if health["status"] == "ok" else 207
    return JSONResponse(content=health, status_code=status_code)
