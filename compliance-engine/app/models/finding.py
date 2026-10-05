"""
Unified Compliance Finding — Pydantic models + SQLAlchemy ORM.

Chuẩn hóa output từ 3 sources: Kyverno, Trivy, kube-bench
về một schema chung để scorer và recommender xử lý đồng nhất.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ComplianceCategory(str, Enum):
    """4 compliance domains với trọng số scoring."""

    CLUSTER_SECURITY = "cluster_security"  # Weight: 0.35  — CIS control plane / etcd / network
    WORKLOAD_SECURITY = "workload_security"  # Weight: 0.35  — Pod security context / RBAC
    SUPPLY_CHAIN = "supply_chain"  # Weight: 0.20  — Image CVEs / registry / tag policy
    PLATFORM_CONFIG = "platform_config"  # Weight: 0.10  — Labels / limits / probes


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


# ---------------------------------------------------------------------------
# Nested value objects
# ---------------------------------------------------------------------------


class K8sResource(BaseModel):
    """Định danh Kubernetes resource liên quan tới finding."""

    kind: str  # "Deployment", "Pod", "Node"...
    name: str
    namespace: Optional[str] = None  # None cho cluster-scoped resources


# ---------------------------------------------------------------------------
# Pydantic — Unified Finding (in-memory, API responses)
# ---------------------------------------------------------------------------


class UnifiedComplianceFinding(BaseModel):
    """
    Schema chuẩn hóa từ tất cả collectors.

    finding_id format:
      - Kyverno:    KYV-<policy-name>-<resource>  e.g. KYV-require-run-as-non-root-web-api
      - Trivy:      TRV-<CVE-ID>-<resource>       e.g. TRV-CVE-2024-1234-nginx-deployment
      - kube-bench: CIS-<section>.<test-id>        e.g. CIS-1.2.3
    """

    finding_id: str = Field(..., description="Unique finding identifier")
    source: Literal["kyverno", "trivy", "kube-bench"]
    category: ComplianceCategory
    severity: Severity
    status: FindingStatus
    resource: K8sResource
    title: str
    description: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional raw metadata (không persist, chỉ dùng cho recommender context)
    raw_metadata: Optional[dict[str, Any]] = Field(default=None, exclude=True)


# ---------------------------------------------------------------------------
# Raw finding — output từ collector trước khi normalize
# ---------------------------------------------------------------------------


class RawFinding(BaseModel):
    """Output thô từ collector, chưa qua normalizer."""

    source: Literal["kyverno", "trivy", "kube-bench"]
    raw_data: dict[str, Any]


# ---------------------------------------------------------------------------
# SQLAlchemy ORM — FindingRecord (persist to PostgreSQL)
# ---------------------------------------------------------------------------


class FindingRecord(Base):
    """ORM model để lưu findings vào PostgreSQL."""

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)

    # Finding identity
    finding_id = Column(String(255), nullable=False, index=True)
    source = Column(String(50), nullable=False)

    # Classification
    category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False)

    # Resource info
    resource_kind = Column(String(100), nullable=False)
    resource_name = Column(String(255), nullable=False)
    resource_namespace = Column(String(255), nullable=True, index=True)

    # Human-readable
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    scan = relationship("ScanRecord", back_populates="findings")

    def to_unified(self) -> UnifiedComplianceFinding:
        """Convert ORM record → Pydantic model."""
        return UnifiedComplianceFinding(
            finding_id=self.finding_id,
            source=self.source,  # type: ignore[arg-type]
            category=ComplianceCategory(self.category),
            severity=Severity(self.severity),
            status=FindingStatus(self.status),
            resource=K8sResource(
                kind=self.resource_kind,
                name=self.resource_name,
                namespace=self.resource_namespace,
            ),
            title=self.title,
            description=self.description or "",
            collected_at=self.collected_at,
        )
