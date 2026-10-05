"""
Redis cache wrapper cho Compliance Engine.

Caching strategy:
- Scores (namespace level):  TTL 5 phút  — invalidate khi scan xong
- Findings list:             TTL 5 phút  — invalidate khi scan xong
- AI Recommendations:        TTL 30 phút — tốn kém để tái tạo
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.models.score import ScoreResult

logger = logging.getLogger(__name__)

# Cache key prefixes
KEY_SCORES = "scores"
KEY_FINDINGS = "findings"
KEY_AI_REC = "ai_rec"
KEY_DOMAINS = "domains"


class ComplianceCache:
    """Async Redis wrapper cho compliance data caching."""

    def __init__(self, redis_url: str, ttl_scores: int = 300, ttl_findings: int = 300, ttl_ai_rec: int = 1800):
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = redis_url
        self.TTL_SCORES = ttl_scores
        self.TTL_FINDINGS = ttl_findings
        self.TTL_AI_REC = ttl_ai_rec

    async def connect(self) -> None:
        """Tạo Redis connection pool."""
        self._redis = await aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis connected: %s", self._redis_url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed")

    def _redis_client(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    # -----------------------------------------------------------------------
    # Scores
    # -----------------------------------------------------------------------

    async def get_scores(self, namespace: str = "all") -> Optional[ScoreResult]:
        """Lấy cached score result cho namespace."""
        try:
            cached = await self._redis_client().get(f"{KEY_SCORES}:{namespace}")
            if cached:
                return ScoreResult.model_validate_json(cached)
        except Exception as e:
            logger.warning("Redis get_scores error: %s", e)
        return None

    async def set_scores(self, result: ScoreResult, namespace: str = "all") -> None:
        """Cache score result với TTL."""
        try:
            await self._redis_client().setex(
                f"{KEY_SCORES}:{namespace}",
                self.TTL_SCORES,
                result.model_dump_json(),
            )
        except Exception as e:
            logger.warning("Redis set_scores error: %s", e)

    async def invalidate_scores(self, namespace: str = "all") -> None:
        """Xóa cached score khi có scan mới."""
        try:
            await self._redis_client().delete(f"{KEY_SCORES}:{namespace}")
            logger.debug("Invalidated scores cache: namespace=%s", namespace)
        except Exception as e:
            logger.warning("Redis invalidate_scores error: %s", e)

    # -----------------------------------------------------------------------
    # Findings
    # -----------------------------------------------------------------------

    async def get_findings(self, cache_key: str) -> Optional[list[dict]]:
        """Lấy cached findings list."""
        try:
            cached = await self._redis_client().get(f"{KEY_FINDINGS}:{cache_key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Redis get_findings error: %s", e)
        return None

    async def set_findings(self, cache_key: str, findings: list[dict]) -> None:
        try:
            await self._redis_client().setex(
                f"{KEY_FINDINGS}:{cache_key}",
                self.TTL_FINDINGS,
                json.dumps(findings),
            )
        except Exception as e:
            logger.warning("Redis set_findings error: %s", e)

    # -----------------------------------------------------------------------
    # AI Recommendations
    # -----------------------------------------------------------------------

    async def get_ai_recommendation(self, finding_id: str, strategy: str) -> Optional[dict]:
        """Lấy cached AI recommendation (costly to regenerate)."""
        try:
            cached = await self._redis_client().get(f"{KEY_AI_REC}:{finding_id}:{strategy}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Redis get_ai_recommendation error: %s", e)
        return None

    async def set_ai_recommendation(self, finding_id: str, strategy: str, rec: dict) -> None:
        try:
            await self._redis_client().setex(
                f"{KEY_AI_REC}:{finding_id}:{strategy}",
                self.TTL_AI_REC,
                json.dumps(rec),
            )
        except Exception as e:
            logger.warning("Redis set_ai_recommendation error: %s", e)

    # -----------------------------------------------------------------------
    # Bulk invalidation — dùng sau khi scan hoàn thành
    # -----------------------------------------------------------------------

    async def invalidate_all_scan_results(self) -> None:
        """Xóa tất cả cached scores và findings sau khi có scan mới."""
        try:
            redis = self._redis_client()
            keys_to_delete = []
            async for key in redis.scan_iter(f"{KEY_SCORES}:*"):
                keys_to_delete.append(key)
            async for key in redis.scan_iter(f"{KEY_FINDINGS}:*"):
                keys_to_delete.append(key)
            async for key in redis.scan_iter(f"{KEY_DOMAINS}:*"):
                keys_to_delete.append(key)
            if keys_to_delete:
                await redis.delete(*keys_to_delete)
                logger.info("Invalidated %d cache keys after scan", len(keys_to_delete))
        except Exception as e:
            logger.warning("Redis bulk invalidate error: %s", e)

    async def ping(self) -> bool:
        """Health check — trả về True nếu Redis healthy."""
        try:
            return await self._redis_client().ping()
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # Generic JSON store — dùng cho AI summaries và arbitrary payloads
    # -----------------------------------------------------------------------

    async def get_json(self, key: str) -> Optional[dict]:
        """Get arbitrary JSON object from Redis."""
        try:
            cached = await self._redis_client().get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Redis get_json error key=%s: %s", key, e)
        return None

    async def set_json(self, key: str, value: dict, ttl: int = 1800) -> None:
        """Set arbitrary JSON object in Redis with TTL."""
        try:
            await self._redis_client().setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning("Redis set_json error key=%s: %s", key, e)

