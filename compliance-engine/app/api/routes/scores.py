"""
Scores routes — GET /api/v1/scores, /scores/{namespace}, /scores/history, /domains

Trả về compliance scores với Redis caching.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import CacheClient, DBSession
from app.models.score import ScoreRecord, ScoreResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("", response_model=dict)
async def get_latest_scores(
    db: DBSession,
    cache: CacheClient,
) -> dict:
    """
    Get latest compliance scores (cluster-wide).

    Response được cache trong Redis 5 phút.
    """
    # Try cache first
    cached = await cache.get_scores("all")
    if cached:
        logger.debug("Scores cache hit: namespace=all")
        return {"cached": True, **cached.model_dump()}

    # Query DB
    result = await db.execute(
        select(ScoreRecord)
        .order_by(ScoreRecord.scanned_at.desc())
        .limit(1)
    )
    score_record = result.scalar_one_or_none()

    if not score_record:
        raise HTTPException(status_code=404, detail="No scores available. Run a scan first.")

    score_result = score_record.to_score_result()

    # Cache và return
    await cache.set_scores(score_result, "all")
    return {"cached": False, **score_result.model_dump()}


@router.get("/history")
async def get_scores_history(
    db: DBSession,
    limit: int = Query(10, ge=1, le=50, description="Number of historical scores"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
) -> dict:
    """
    Get score history for trend chart.

    Trả về N scans gần nhất để vẽ trend line chart trong Backstage plugin.
    """
    query = select(ScoreRecord).order_by(ScoreRecord.scanned_at.desc()).limit(limit)
    if namespace:
        query = query.where(ScoreRecord.namespace == namespace)

    result = await db.execute(query)
    records = result.scalars().all()

    history = [
        {
            "scan_id": r.scan_id,
            "overall_score": r.overall_score,
            "classification": r.classification,
            "scanned_at": r.scanned_at.isoformat(),
            "total_findings": r.total_findings or 0,
            "total_failed": r.total_failed or 0,
        }
        for r in reversed(records)  # Chronological order for chart
    ]

    return {"history": history, "count": len(history)}


@router.get("/{namespace}")
async def get_namespace_scores(
    namespace: str,
    db: DBSession,
    cache: CacheClient,
) -> dict:
    """Get latest compliance scores for a specific namespace."""
    # Try cache
    cached = await cache.get_scores(namespace)
    if cached:
        return {"cached": True, **cached.model_dump()}

    result = await db.execute(
        select(ScoreRecord)
        .where(ScoreRecord.namespace == namespace)
        .order_by(ScoreRecord.scanned_at.desc())
        .limit(1)
    )
    score_record = result.scalar_one_or_none()

    if not score_record:
        raise HTTPException(
            status_code=404,
            detail=f"No scores for namespace '{namespace}'. Run a scan with namespace filter.",
        )

    score_result = score_record.to_score_result()
    await cache.set_scores(score_result, namespace)
    return {"cached": False, **score_result.model_dump()}
