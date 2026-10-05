"""
Scan routes — POST /api/v1/scan, GET /api/v1/scan/{id}, GET /api/v1/scans

Trigger compliance scan và theo dõi trạng thái.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.dependencies import CacheClient, DBSession
from app.models.finding import FindingRecord
from app.models.scan import ScanRecord, ScanStatus
from app.models.score import ScoreRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["scan"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    namespace: Optional[str] = None  # None = cluster-wide scan


class ScanResponse(BaseModel):
    scan_id: int
    status: str
    namespace_filter: Optional[str]
    started_at: datetime
    message: str


class ScanDetailResponse(BaseModel):
    scan_id: int
    status: str
    namespace_filter: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    total_findings: int
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=ScanResponse, status_code=202)
async def trigger_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
    cache: CacheClient,
) -> ScanResponse:
    """
    Trigger a new compliance scan.

    Scan chạy background — response trả về ngay với scan_id.
    Poll GET /api/v1/scans/{scan_id} để theo dõi progress.
    """
    # Tạo ScanRecord với status PENDING
    scan = ScanRecord(
        status=ScanStatus.PENDING,
        started_at=datetime.utcnow(),
        namespace_filter=request.namespace,
    )
    db.add(scan)
    await db.flush()  # Get scan.id
    await db.commit()

    # Run scan in background
    background_tasks.add_task(_run_scan_background, scan.id, request.namespace, cache)

    return ScanResponse(
        scan_id=scan.id,
        status=ScanStatus.PENDING,
        namespace_filter=request.namespace,
        started_at=scan.started_at,
        message=f"Scan {scan.id} queued. Poll GET /api/v1/scans/{scan.id} for status.",
    )


@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(scan_id: int, db: DBSession) -> ScanDetailResponse:
    """Get scan details và status."""
    result = await db.execute(select(ScanRecord).where(ScanRecord.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return ScanDetailResponse(
        scan_id=scan.id,
        status=scan.status,
        namespace_filter=scan.namespace_filter,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        total_findings=scan.total_findings or 0,
        error_message=scan.error_message,
    )


@router.get("", tags=["scan"])
async def list_scans(
    db: DBSession,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """List all scans (paginated), newest first."""
    result = await db.execute(
        select(ScanRecord)
        .order_by(ScanRecord.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    scans = result.scalars().all()

    count_result = await db.execute(select(func.count(ScanRecord.id)))
    total = count_result.scalar_one()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "scans": [
            {
                "scan_id": s.id,
                "status": s.status,
                "namespace_filter": s.namespace_filter,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "total_findings": s.total_findings or 0,
            }
            for s in scans
        ],
    }


# ---------------------------------------------------------------------------
# Background scan task
# ---------------------------------------------------------------------------


async def _run_scan_background(
    scan_id: int,
    namespace: Optional[str],
    cache: CacheClient,
) -> None:
    """
    Background task: Thu thập → normalize → score → persist.

    Import các dependencies ở đây để tránh circular imports.
    """
    from app.database import get_session_factory
    from app.collector.aggregator import ComplianceAggregator
    from app.normalizer.mapper import NormalizerMapper
    from app.scorer.engine import ComplianceScorer
    from app.models.finding import FindingRecord
    from app.models.score import ScoreRecord

    factory = get_session_factory()

    async with factory() as db:
        try:
            # Update status → RUNNING
            result = await db.execute(select(ScanRecord).where(ScanRecord.id == scan_id))
            scan = result.scalar_one()
            scan.status = ScanStatus.RUNNING
            await db.commit()

            # Get K8s client from module-level state
            from app.main import app as _app
            k8s_client = getattr(_app.state, "k8s_client", None)

            if k8s_client is None:
                raise RuntimeError("K8s client not available — are you running in-cluster?")

            # 1. Collect
            aggregator = ComplianceAggregator(k8s_client)
            raw_findings = await aggregator.collect_all(namespace)

            # 2. Normalize
            mapper = NormalizerMapper()
            unified_findings = mapper.normalize_all(raw_findings)

            # 3. Score
            scorer = ComplianceScorer()
            score_result = scorer.calculate(unified_findings, scan_id, namespace)

            # 4. Persist findings
            for uf in unified_findings:
                record = FindingRecord(
                    scan_id=scan_id,
                    finding_id=uf.finding_id,
                    source=uf.source,
                    category=uf.category.value,
                    severity=uf.severity.value,
                    status=uf.status.value,
                    resource_kind=uf.resource.kind,
                    resource_name=uf.resource.name,
                    resource_namespace=uf.resource.namespace,
                    title=uf.title,
                    description=uf.description,
                    collected_at=uf.collected_at,
                )
                db.add(record)

            # 5. Persist score
            score_record = ScoreRecord(
                scan_id=scan_id,
                overall_score=score_result.overall_score,
                classification=score_result.classification.value,
                domain_scores=[d.model_dump() for d in score_result.domains],
                namespace=namespace,
                scanned_at=score_result.scanned_at,
                total_findings=score_result.total_findings,
                total_passed=score_result.total_passed,
                total_failed=score_result.total_failed,
                critical_violations=score_result.critical_violations,
                high_violations=score_result.high_violations,
            )
            db.add(score_record)

            # 6. Update scan status
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.total_findings = len(unified_findings)
            await db.commit()

            # 7. Invalidate cache
            await cache.invalidate_all_scan_results()

            logger.info(
                "Scan %d completed: %d findings, score=%.1f (%s)",
                scan_id,
                len(unified_findings),
                score_result.overall_score,
                score_result.classification.value,
            )

        except Exception as e:
            logger.error("Scan %d failed: %s", scan_id, e, exc_info=True)
            try:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)[:1000]
                scan.completed_at = datetime.utcnow()
                await db.commit()
            except Exception:
                pass
