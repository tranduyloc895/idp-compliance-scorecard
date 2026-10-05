"""
Recommendation models — Rule-based và AI-generated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.database import Base


# ---------------------------------------------------------------------------
# Pydantic — in-memory / API response models
# ---------------------------------------------------------------------------


class RuleRecommendation(BaseModel):
    """
    Recommendation được sinh bởi rule-based engine.
    Deterministic, nhanh (<1ms), coverage giới hạn ở 20-30 rules.
    """

    finding_id: str
    rule_id: str  # e.g. "require-run-as-non-root"
    title: str
    fix_description: str
    yaml_fix: str  # Content của fix template
    reference: str  # CIS Benchmark / NIST reference
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AIRecommendation(BaseModel):
    """
    Recommendation được sinh bởi Gemini 2.5 Flash.
    Structured output (JSON mode) — coverage rộng hơn rule-based.

    Dùng cho 2 strategies so sánh:
    - basic: prompt đơn giản, không có context bổ sung
    - context_enriched: có CIS Benchmark + K8s security docs context
    """

    finding_id: str
    strategy_used: Literal["basic", "context_enriched"] = "context_enriched"
    model: str = "gemini-2.5-flash"

    # AI-generated content (structured output fields)
    root_cause: str
    yaml_fix: str  # Drop-in YAML, copy-paste ready
    impact_if_unfixed: str
    cis_references: list[str] = Field(default_factory=list)  # ["5.2.6", "5.2.7"]
    urgency: Literal["immediate", "soon", "low"] = "soon"
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="AI confidence score 0-1")

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None  # Latency đo cho thực nghiệm


# ---------------------------------------------------------------------------
# SQLAlchemy ORM — persist recommendations
# ---------------------------------------------------------------------------


class RecommendationRecord(Base):
    """ORM model lưu recommendations (cả rule-based và AI) vào PostgreSQL."""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    finding_id = Column(String(255), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=True)

    rec_type = Column(String(20), nullable=False)  # "rule" | "ai"
    strategy = Column(String(30), nullable=True)  # "basic" | "context_enriched" (AI only)
    model = Column(String(100), nullable=True)  # AI model name

    title = Column(String(500), nullable=True)
    fix_description = Column(Text, nullable=True)
    yaml_fix = Column(Text, nullable=True)
    reference = Column(String(500), nullable=True)

    # AI-specific
    root_cause = Column(Text, nullable=True)
    impact_if_unfixed = Column(Text, nullable=True)
    cis_references = Column(JSON, nullable=True)  # list[str]
    urgency = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)

    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
