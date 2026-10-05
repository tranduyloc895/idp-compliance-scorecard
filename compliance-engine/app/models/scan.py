"""
ScanRecord — ORM model tracking scan lifecycle.

Mỗi lần gọi POST /api/v1/scan tạo 1 ScanRecord.
Tất cả findings + scores liên kết qua scan_id.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanRecord(Base):
    """ORM model theo dõi trạng thái scan."""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False, default=ScanStatus.PENDING)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Optional filter — nếu scan chỉ 1 namespace
    namespace_filter = Column(String(255), nullable=True)

    # Summary (populated khi scan complete)
    total_findings = Column(Integer, default=0)
    error_message = Column(String(1000), nullable=True)

    # Relationships
    findings = relationship("FindingRecord", back_populates="scan", cascade="all, delete-orphan")
    scores = relationship("ScoreRecord", back_populates="scan", cascade="all, delete-orphan")
    ai_summaries = relationship("AISummaryRecord", back_populates="scan", cascade="all, delete-orphan")
