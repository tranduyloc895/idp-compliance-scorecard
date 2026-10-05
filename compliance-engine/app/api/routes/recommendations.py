"""
Recommendations routes.

GET /api/v1/findings/{id}/recommendation      — Rule-based
GET /api/v1/findings/{id}/ai-recommendation   — AI (Gemini) với optional ?strategy=basic|context_enriched
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import AIRec, CacheClient, DBSession, RuleRec
from app.models.finding import FindingRecord

logger = logging.getLogger(__name__)
router = APIRouter(tags=["recommendations"])


@router.get("/findings/{finding_db_id}/recommendation")
async def get_rule_recommendation(
    finding_db_id: int,
    db: DBSession,
    rule_rec: RuleRec,
) -> dict:
    """
    Get rule-based recommendation cho finding.

    Deterministic, <1ms latency.
    Trả về 404 nếu finding không có rule phù hợp.
    """
    finding_record = await _get_finding_record(finding_db_id, db)
    unified = finding_record.to_unified()

    recommendation = rule_rec.get_recommendation(unified)

    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No rule-based recommendation available for finding '{unified.finding_id}'. "
                f"Use /ai-recommendation for unseen violations."
            ),
        )

    return {
        "finding_id": recommendation.finding_id,
        "type": "rule_based",
        "rule_id": recommendation.rule_id,
        "title": recommendation.title,
        "fix_description": recommendation.fix_description,
        "yaml_fix": recommendation.yaml_fix,
        "reference": recommendation.reference,
        "generated_at": recommendation.generated_at.isoformat(),
        "latency_ms": 0,  # Rule-based is instant
    }


@router.get("/findings/{finding_db_id}/ai-recommendation")
async def get_ai_recommendation(
    finding_db_id: int,
    db: DBSession,
    cache: CacheClient,
    ai_rec: AIRec,
    strategy: Literal["basic", "context_enriched"] = Query(
        "context_enriched",
        description="Prompt strategy for AI recommendation comparison",
    ),
) -> dict:
    """
    Get AI recommendation từ Gemini 2.5 Flash.

    Cached trong Redis 30 phút per (finding_id, strategy).

    Query param ?strategy=basic | context_enriched (default: context_enriched)
    Dùng cho thực nghiệm so sánh 2 prompt strategies.
    """
    if ai_rec is None:
        raise HTTPException(
            status_code=503,
            detail="AI recommender not available. Set GEMINI_API_KEY environment variable.",
        )

    finding_record = await _get_finding_record(finding_db_id, db)
    unified = finding_record.to_unified()

    # Try cache
    cached = await cache.get_ai_recommendation(unified.finding_id, strategy)
    if cached:
        logger.debug("AI recommendation cache hit: finding=%s strategy=%s", unified.finding_id, strategy)
        return {"cached": True, **cached}

    # Generate new recommendation
    try:
        recommendation = await ai_rec.recommend(unified, strategy=strategy)
    except Exception as e:
        logger.error("AI recommendation error: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"AI recommendation generation failed: {str(e)[:200]}",
        )

    result = {
        "finding_id": recommendation.finding_id,
        "type": "ai_generated",
        "strategy": recommendation.strategy_used,
        "model": recommendation.model,
        "root_cause": recommendation.root_cause,
        "yaml_fix": recommendation.yaml_fix,
        "impact_if_unfixed": recommendation.impact_if_unfixed,
        "cis_references": recommendation.cis_references,
        "urgency": recommendation.urgency,
        "confidence": recommendation.confidence,
        "latency_ms": recommendation.latency_ms,
        "generated_at": recommendation.generated_at.isoformat(),
    }

    # Cache
    await cache.set_ai_recommendation(unified.finding_id, strategy, result)

    return {"cached": False, **result}


@router.get("/findings/{finding_db_id}/compare-recommendations")
async def compare_recommendations(
    finding_db_id: int,
    db: DBSession,
    cache: CacheClient,
    ai_rec: AIRec,
    rule_rec: RuleRec,
) -> dict:
    """
    So sánh tất cả 3 recommendation approaches cho 1 finding.

    Endpoint đặc biệt cho thực nghiệm research:
    - Rule-based recommendation
    - AI Basic prompt
    - AI Context-enriched prompt

    Trả về cả 3 để dễ so sánh.
    """
    if ai_rec is None:
        raise HTTPException(status_code=503, detail="AI recommender not available")

    finding_record = await _get_finding_record(finding_db_id, db)
    unified = finding_record.to_unified()

    # Rule-based (sync, fast)
    rule_result = rule_rec.get_recommendation(unified)

    # AI both strategies (async parallel)
    both_ai = await ai_rec.recommend_both_strategies(unified)

    response = {
        "finding_id": unified.finding_id,
        "finding_title": unified.title,
        "finding_severity": unified.severity.value,
        "recommendations": {
            "rule_based": (
                {
                    "available": True,
                    "rule_id": rule_result.rule_id,
                    "title": rule_result.title,
                    "fix_description": rule_result.fix_description,
                    "yaml_fix": rule_result.yaml_fix,
                    "reference": rule_result.reference,
                    "latency_ms": 0,
                }
                if rule_result
                else {"available": False, "reason": "No matching rule"}
            ),
            "ai_basic": (
                {
                    "available": True,
                    **both_ai["basic"].model_dump(),
                }
                if "basic" in both_ai
                else {"available": False}
            ),
            "ai_context_enriched": (
                {
                    "available": True,
                    **both_ai["context_enriched"].model_dump(),
                }
                if "context_enriched" in both_ai
                else {"available": False}
            ),
        },
    }

    return response


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


async def _get_finding_record(finding_db_id: int, db) -> FindingRecord:
    """Lấy FindingRecord từ DB, raise 404 nếu không tìm thấy."""
    result = await db.execute(
        select(FindingRecord).where(FindingRecord.id == finding_db_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_db_id} not found")
    return finding
