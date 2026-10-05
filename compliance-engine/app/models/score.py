"""
Score models — Pydantic + SQLAlchemy.

Kết quả scoring sau khi aggregate tất cả findings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.finding import ComplianceCategory


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Classification(str, Enum):
    """Phân loại tổng thể compliance score."""

    EXCELLENT = "excellent"  # 90–100  🟢  Best practice level
    GOOD = "good"  # 75–89   🔵  Production ready
    FAIR = "fair"  # 60–74   🟡  Needs improvement
    POOR = "poor"  # <60     🔴  High risk


# ---------------------------------------------------------------------------
# Pydantic — in-memory / API response models
# ---------------------------------------------------------------------------


class DomainScore(BaseModel):
    """Score của một compliance domain."""

    domain: ComplianceCategory
    score: float = Field(..., ge=0.0, le=100.0, description="0-100 weighted domain score")
    weight: float = Field(..., ge=0.0, le=1.0, description="Domain weight in overall score")

    # Counters
    total_checks: int = Field(0, ge=0)
    passed: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    warned: int = Field(0, ge=0)

    # Severity breakdown (failed only)
    critical_count: int = Field(0, ge=0)
    high_count: int = Field(0, ge=0)
    medium_count: int = Field(0, ge=0)
    low_count: int = Field(0, ge=0)

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 100.0
        return round(self.passed / self.total_checks * 100, 2)


class ScoreResult(BaseModel):
    """Full scoring result cho một scan."""

    scan_id: int
    overall_score: float = Field(..., ge=0.0, le=100.0)
    classification: Classification

    domains: list[DomainScore]

    # Scan context
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    namespace: Optional[str] = None  # None = cluster-wide

    # Summary
    total_findings: int = Field(0, ge=0)
    total_passed: int = Field(0, ge=0)
    total_failed: int = Field(0, ge=0)

    # Penalty summary
    critical_violations: int = Field(0, ge=0)
    high_violations: int = Field(0, ge=0)

    def get_domain(self, category: ComplianceCategory) -> Optional[DomainScore]:
        """Lookup domain score by category."""
        for d in self.domains:
            if d.domain == category:
                return d
        return None


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------


class ScoreRecord(Base):
    """ORM model để persist ScoreResult vào PostgreSQL."""

    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)

    overall_score = Column(Float, nullable=False)
    classification = Column(String(20), nullable=False)

    # Domain scores stored as JSON blob
    domain_scores = Column(JSON, nullable=False)  # list[dict] serialized

    namespace = Column(String(255), nullable=True, index=True)
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Summary counters (denormalized for quick querying)
    total_findings = Column(Integer, default=0)
    total_passed = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    critical_violations = Column(Integer, default=0)
    high_violations = Column(Integer, default=0)

    scan = relationship("ScanRecord", back_populates="scores")

    def to_score_result(self) -> ScoreResult:
        """Reconstruct Pydantic model từ ORM record."""
        domains = [DomainScore(**d) for d in self.domain_scores]
        return ScoreResult(
            scan_id=self.scan_id,
            overall_score=self.overall_score,
            classification=Classification(self.classification),
            domains=domains,
            scanned_at=self.scanned_at,
            namespace=self.namespace,
            total_findings=self.total_findings or 0,
            total_passed=self.total_passed or 0,
            total_failed=self.total_failed or 0,
            critical_violations=self.critical_violations or 0,
            high_violations=self.high_violations or 0,
        )
