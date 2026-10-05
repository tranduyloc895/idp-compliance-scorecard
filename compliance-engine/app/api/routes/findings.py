"""
Findings routes — GET /api/v1/findings, /findings/{id}

List và filter compliance findings với Redis caching.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, select, func

from app.api.dependencies import CacheClient, DBSession
from app.models.finding import ComplianceCategory, FindingRecord, FindingStatus, Severity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("")
async def list_findings(
    db: DBSession,
    cache: CacheClient,
    # Filters
    severity: Optional[str] = Query(None, description="Filter by severity: critical,high,medium,low,info"),
    category: Optional[str] = Query(None, description="Filter by category: cluster_security,workload_security,supply_chain,platform_config"),
    status: Optional[str] = Query(None, description="Filter by status: pass,fail,warn"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    source: Optional[str] = Query(None, description="Filter by source: kyverno,trivy,kube-bench"),
    scan_id: Optional[int] = Query(None, description="Filter by specific scan ID"),
    # Pagination
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    List compliance findings với filter và pagination.

    Response cached trong Redis 5 phút (per filter combination).
    """
    # Build cache key từ query params
    cache_key = hashlib.md5(
        f"{severity}:{category}:{status}:{namespace}:{source}:{scan_id}:{limit}:{offset}".encode()
    ).hexdigest()

    cached = await cache.get_findings(cache_key)
    if cached:
        return {"cached": True, "data": cached}

    # Build query
    conditions = []
    if severity:
        conditions.append(FindingRecord.severity == severity.lower())
    if category:
        conditions.append(FindingRecord.category == category.lower())
    if status:
        conditions.append(FindingRecord.status == status.lower())
    if namespace:
        conditions.append(FindingRecord.resource_namespace == namespace)
    if source:
        conditions.append(FindingRecord.source == source.lower())
    if scan_id:
        conditions.append(FindingRecord.scan_id == scan_id)

    query = (
        select(FindingRecord)
        .order_by(
            FindingRecord.severity.asc(),  # CRITICAL first (alphabetically c < h < l < m)
            FindingRecord.collected_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count(FindingRecord.id))

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    result = await db.execute(query)
    findings = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    data = {
        "total": total,
        "limit": limit,
        "offset": offset,
        "findings": [
            {
                "id": f.id,
                "finding_id": f.finding_id,
                "source": f.source,
                "category": f.category,
                "severity": f.severity,
                "status": f.status,
                "resource_kind": f.resource_kind,
                "resource_name": f.resource_name,
                "resource_namespace": f.resource_namespace,
                "title": f.title,
                "description": f.description,
                "collected_at": f.collected_at.isoformat(),
                "scan_id": f.scan_id,
            }
            for f in findings
        ],
    }

    # Cache result
    await cache.set_findings(cache_key, data)

    return {"cached": False, "data": data}


@router.get("/{finding_db_id}")
async def get_finding(finding_db_id: int, db: DBSession) -> dict:
    """Get finding detail by database ID."""
    result = await db.execute(
        select(FindingRecord).where(FindingRecord.id == finding_db_id)
    )
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_db_id} not found")

    return {
        "id": finding.id,
        "finding_id": finding.finding_id,
        "source": finding.source,
        "category": finding.category,
        "severity": finding.severity,
        "status": finding.status,
        "resource": {
            "kind": finding.resource_kind,
            "name": finding.resource_name,
            "namespace": finding.resource_namespace,
        },
        "title": finding.title,
        "description": finding.description,
        "collected_at": finding.collected_at.isoformat(),
        "scan_id": finding.scan_id,
    }
