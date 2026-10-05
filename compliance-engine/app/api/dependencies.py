"""
FastAPI dependency injection container.

Cung cấp các shared dependencies:
- DB session (PostgreSQL)
- Redis cache
- K8s client
- Recommenders
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import ComplianceCache
from app.database import get_session
from app.recommender.ai_recommender import AIRecommender
from app.recommender.rules import RuleBasedRecommender


# ---------------------------------------------------------------------------
# DB Session dependency
# ---------------------------------------------------------------------------

async def get_db(request: Request) -> AsyncSession:
    """Inject async DB session từ app state."""
    async for session in get_session():
        yield session


# ---------------------------------------------------------------------------
# Cache dependency
# ---------------------------------------------------------------------------

async def get_cache(request: Request) -> ComplianceCache:
    """Inject Redis cache từ app state."""
    cache: ComplianceCache = request.app.state.cache
    return cache


# ---------------------------------------------------------------------------
# K8s client dependency
# ---------------------------------------------------------------------------

async def get_k8s_client(request: Request):
    """Inject Kubernetes API client từ app state."""
    return request.app.state.k8s_client


# ---------------------------------------------------------------------------
# Recommender dependencies
# ---------------------------------------------------------------------------

# Rule-based recommender — stateless singleton
_rule_recommender = RuleBasedRecommender()


def get_rule_recommender() -> RuleBasedRecommender:
    """Inject rule-based recommender."""
    return _rule_recommender


async def get_ai_recommender(request: Request) -> Optional[AIRecommender]:
    """Inject AI recommender từ app state (None nếu không có API key)."""
    return getattr(request.app.state, "ai_recommender", None)


# ---------------------------------------------------------------------------
# Typed aliases (dùng Annotated để giảm boilerplate trong routes)
# ---------------------------------------------------------------------------

DBSession = Annotated[AsyncSession, Depends(get_db)]
CacheClient = Annotated[ComplianceCache, Depends(get_cache)]
RuleRec = Annotated[RuleBasedRecommender, Depends(get_rule_recommender)]
AIRec = Annotated[Optional[AIRecommender], Depends(get_ai_recommender)]
