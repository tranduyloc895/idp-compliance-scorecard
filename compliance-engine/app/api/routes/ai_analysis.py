"""
AI Analysis Routes — Part 2 of Compliance Dashboard implementation.

Endpoints:
  GET  /api/v1/ai/summary           — AI executive security summary
  GET  /api/v1/ai/remediation-plan  — AI-generated prioritized fix plan
  POST /api/v1/ai/batch-analyze     — Batch AI recommendation for multiple findings

All endpoints require AI recommender to be initialized (GEMINI_API_KEY set).
Results are cached in Redis (30min TTL) and persisted to PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.ai_summary import AISummary, RemediationPlan, AISummaryRecord
from app.models.finding import UnifiedComplianceFinding, FindingRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------


class BatchAnalyzeRequest(BaseModel):
    finding_ids: list[str] = Field(..., min_length=1, max_length=50)
    strategy: str = Field(default="context_enriched", pattern="^(basic|context_enriched)$")


class BatchAnalyzeResponse(BaseModel):
    results: list[dict] = []
    successful: int = 0
    failed: int = 0
    total_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Helper — get AI recommender from app state
# ---------------------------------------------------------------------------


def _get_recommender(request: Request):
    rec = getattr(request.app.state, "ai_recommender", None)
    if rec is None:
        raise HTTPException(
            status_code=503,
            detail="AI Recommender not available. Set GEMINI_API_KEY to enable AI features.",
        )
    return rec


async def _load_latest_findings(db: AsyncSession) -> list[UnifiedComplianceFinding]:
    """Load findings từ scan gần nhất."""
    from sqlalchemy import select, desc
    from app.models.scan import ScanRecord

    # Get latest completed scan
    result = await db.execute(
        select(ScanRecord)
        .where(ScanRecord.status == "completed")
        .order_by(desc(ScanRecord.id))
        .limit(1)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return []

    # Load findings for that scan
    result = await db.execute(
        select(FindingRecord).where(FindingRecord.scan_id == scan.id)
    )
    records = result.scalars().all()
    return [r.to_unified() for r in records]


async def _load_latest_score(db: AsyncSession):
    """Load score từ scan gần nhất."""
    from sqlalchemy import select, desc
    from app.models.score import ScoreRecord

    result = await db.execute(
        select(ScoreRecord).order_by(desc(ScoreRecord.id)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None
    return record.to_score_result()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=AISummary, summary="AI Executive Security Summary")
async def get_ai_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (or fetch cached) AI executive summary từ scan gần nhất.

    - Calls Gemini 2.5 Flash với EXECUTIVE_SUMMARY_PROMPT
    - Cached in Redis for 30min (TTL from settings)
    - Persisted to PostgreSQL ai_summaries table
    - Returns: overall_assessment, risk_level, top_priorities, remediation_phases, trend_prediction

    **Thesis note**: latency_ms in response is Gemini API latency for experiments.
    """
    cache = getattr(request.app.state, "cache", None)

    # Check Redis cache first
    if cache:
        cached = await cache.get_json("ai:summary:latest")
        if cached:
            logger.info("AI summary served from cache")
            return AISummary.model_validate(cached)

    # Load data from DB
    findings = await _load_latest_findings(db)
    if not findings:
        raise HTTPException(status_code=404, detail="No scan data found. Run a scan first.")

    score = await _load_latest_score(db)
    if not score:
        raise HTTPException(status_code=404, detail="No score data found.")

    recommender = _get_recommender(request)

    # Generate summary via Gemini
    summary = await recommender.generate_summary(findings, score)

    # Persist to DB
    try:
        from sqlalchemy import select, desc
        from app.models.scan import ScanRecord
        scan_result = await db.execute(
            select(ScanRecord).where(ScanRecord.status == "completed")
            .order_by(desc(ScanRecord.id)).limit(1)
        )
        latest_scan = scan_result.scalar_one_or_none()
        scan_id = latest_scan.id if latest_scan else None

        record = AISummaryRecord(
            scan_id=scan_id,
            strategy="executive_summary",
            summary_json=summary.model_dump(mode="json"),
            latency_ms=summary.latency_ms,
        )
        db.add(record)
        await db.commit()
    except Exception as e:
        logger.warning("Failed to persist AI summary: %s", e)

    # Cache for 30 minutes
    if cache:
        try:
            await cache.set_json("ai:summary:latest", summary.model_dump(mode="json"), ttl=1800)
        except Exception as e:
            logger.warning("Failed to cache AI summary: %s", e)

    return summary


@router.get(
    "/remediation-plan",
    response_model=RemediationPlan,
    summary="AI Remediation Plan",
)
async def get_remediation_plan(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI-prioritized remediation plan từ scan gần nhất.

    Organizes findings into 3 phases:
    - **immediate**: CRITICAL severity, fix today
    - **this_sprint**: HIGH severity, fix this week
    - **backlog**: MEDIUM/LOW, schedule improvement

    **Thesis note**: latency_ms in response is Gemini API latency.
    """
    cache = getattr(request.app.state, "cache", None)

    # Check cache
    if cache:
        cached = await cache.get_json("ai:remediation-plan:latest")
        if cached:
            logger.info("Remediation plan served from cache")
            return RemediationPlan.model_validate(cached)

    findings = await _load_latest_findings(db)
    if not findings:
        raise HTTPException(status_code=404, detail="No scan data found. Run a scan first.")

    recommender = _get_recommender(request)
    plan = await recommender.generate_remediation_plan(findings)

    # Cache for 30 minutes
    if cache:
        try:
            await cache.set_json("ai:remediation-plan:latest", plan.model_dump(mode="json"), ttl=1800)
        except Exception as e:
            logger.warning("Failed to cache remediation plan: %s", e)

    return plan


@router.post(
    "/batch-analyze",
    response_model=BatchAnalyzeResponse,
    summary="Batch AI Recommendation",
)
async def batch_analyze(
    body: BatchAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Batch AI recommendation for multiple finding IDs.

    Calls Gemini for each finding in parallel.
    Used by CompliancePage to pre-warm recommendations panel.

    **Thesis note**: Useful for measuring aggregate latency across strategies.
    """
    import asyncio
    from sqlalchemy import select

    recommender = _get_recommender(request)

    # Load requested findings
    result = await db.execute(
        select(FindingRecord).where(FindingRecord.finding_id.in_(body.finding_ids))
    )
    records = result.scalars().all()
    findings = [r.to_unified() for r in records]

    if not findings:
        raise HTTPException(status_code=404, detail="No findings found for given IDs.")

    # Batch recommend
    tasks = [
        recommender.recommend(f, strategy=body.strategy)
        for f in findings
    ]
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    ai_results = []
    successful = 0
    failed = 0
    total_latency = 0.0

    for r in results_raw:
        if isinstance(r, Exception):
            failed += 1
            logger.warning("Batch analyze item failed: %s", r)
        else:
            successful += 1
            total_latency += r.latency_ms
            ai_results.append(r.model_dump())

    return BatchAnalyzeResponse(
        results=ai_results,
        successful=successful,
        failed=failed,
        total_latency_ms=round(total_latency, 2),
    )
