"""
AI Summary models — Pydantic + SQLAlchemy ORM.

Lưu kết quả AI executive summary và remediation plan để:
1. Serve frontend dashboard
2. Persist cho thesis experiment data (so sánh latency, quality)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Pydantic — in-memory / API response models
# ---------------------------------------------------------------------------


class PriorityFix(BaseModel):
    """Top priority fix item trong AI summary."""

    finding_id: str = Field(..., description="Finding identifier")
    title: str = Field(..., description="Short human-readable title")
    severity: str = Field(..., description="Severity level")
    fix_summary: str = Field(..., description="1-line fix description")
    estimated_effort: str = Field(
        ...,
        description="Estimated fix effort e.g. '5 min', '30 min', '2 hours'",
    )


class RemediationPhase(BaseModel):
    """Một phase trong remediation plan."""

    phase: Literal["immediate", "this_sprint", "backlog"] = Field(
        ...,
        description="Remediation urgency phase",
    )
    description: str = Field(..., description="Phase description")
    finding_ids: list[str] = Field(
        default_factory=list,
        description="Finding IDs belonging to this phase",
    )
    total_estimated_effort: str = Field(
        ...,
        description="Total estimated effort for this phase",
    )


class AISummary(BaseModel):
    """AI executive security summary — output từ Gemini."""

    overall_assessment: str = Field(
        ...,
        description="2-3 sentence security posture narrative",
    )
    risk_level: Literal["critical", "high", "moderate", "low"] = Field(
        ...,
        description="Overall risk classification",
    )
    top_priorities: list[PriorityFix] = Field(
        default_factory=list,
        description="Top 3 priority fixes",
    )
    remediation_phases: list[RemediationPhase] = Field(
        default_factory=list,
        description="3-phase remediation roadmap",
    )
    trend_prediction: Literal["improving", "stable", "declining"] = Field(
        default="stable",
        description="Security posture trend prediction",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp khi summary được generate",
    )
    latency_ms: float = Field(
        default=0.0,
        description="Gemini API latency in milliseconds",
    )


class RemediationPlan(BaseModel):
    """AI-generated prioritized remediation plan."""

    phases: list[RemediationPhase] = Field(
        default_factory=list,
        description="3-phase remediation roadmap",
    )
    total_findings: int = Field(0, ge=0, description="Total findings covered")
    total_estimated_effort: str = Field(
        ...,
        description="Total effort across all phases",
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM — AISummaryRecord (persist cho thesis experiment)
# ---------------------------------------------------------------------------


class AISummaryRecord(Base):
    """
    ORM model để persist AI summary vào PostgreSQL.

    Lưu cho thesis experiment: so sánh latency và quality giữa các scans.
    """

    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(
        Integer,
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    strategy = Column(String(50), nullable=False, default="executive_summary")
    summary_json = Column(JSON, nullable=False)     # AISummary serialized
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    scan = relationship("ScanRecord", back_populates="ai_summaries", foreign_keys=[scan_id])

    def to_ai_summary(self) -> AISummary:
        """Reconstruct Pydantic model từ ORM record."""
        data = self.summary_json.copy()
        data["latency_ms"] = self.latency_ms or 0.0
        return AISummary.model_validate(data)
