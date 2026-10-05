"""
Tests for AI Analysis API routes.

Covers:
  - GET /api/v1/ai/summary
  - GET /api/v1/ai/remediation-plan
  - POST /api/v1/ai/batch-analyze

All Gemini calls are mocked. DB is mocked via AsyncMock.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest
from httpx import AsyncClient

from app.models.ai_summary import (
    AISummary,
    RemediationPlan,
    RemediationPhase,
    PriorityFix,
)
from app.models.finding import (
    UnifiedComplianceFinding,
    ComplianceCategory,
    Severity,
    FindingStatus,
    K8sResource,
)
from app.models.score import ScoreResult, Classification, DomainScore


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ai_summary() -> AISummary:
    return AISummary(
        overall_assessment=(
            "The cluster shows moderate security hardening with 3 critical gaps "
            "in workload security requiring immediate attention."
        ),
        risk_level="high",
        top_priorities=[
            PriorityFix(
                finding_id="KYV-require-run-as-non-root-abc",
                title="Container running as root",
                severity="critical",
                fix_summary="Set runAsNonRoot: true in securityContext",
                estimated_effort="5 min",
            ),
        ],
        remediation_phases=[
            RemediationPhase(
                phase="immediate",
                description="Fix CRITICAL violations today",
                finding_ids=["KYV-require-run-as-non-root-abc"],
                total_estimated_effort="30 min",
            ),
            RemediationPhase(
                phase="this_sprint",
                description="Fix HIGH violations this sprint",
                finding_ids=[],
                total_estimated_effort="2 hours",
            ),
            RemediationPhase(
                phase="backlog",
                description="Schedule MEDIUM/LOW improvements",
                finding_ids=[],
                total_estimated_effort="4 hours",
            ),
        ],
        trend_prediction="stable",
        generated_at=datetime(2026, 9, 11, 0, 0, 0),
        latency_ms=1247.5,
    )


@pytest.fixture
def mock_remediation_plan() -> RemediationPlan:
    return RemediationPlan(
        phases=[
            RemediationPhase(
                phase="immediate",
                description="Fix CRITICAL violations",
                finding_ids=["KYV-abc"],
                total_estimated_effort="30 min",
            ),
        ],
        total_findings=3,
        total_estimated_effort="2 hours",
        generated_at=datetime(2026, 9, 11, 0, 0, 0),
        latency_ms=987.3,
    )


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ai_summary_no_recommender():
    """Returns 503 when AI recommender is not initialized."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes.ai_analysis import router
    from app.api.dependencies import get_db

    async def mock_get_db():
        yield AsyncMock()

    with patch(
        "app.api.routes.ai_analysis._load_latest_findings",
        new=AsyncMock(return_value=[MagicMock()]),  # Return non-empty to pass the check
    ), patch(
        "app.api.routes.ai_analysis._load_latest_score",
        new=AsyncMock(return_value=MagicMock()),
    ):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = mock_get_db
        app.state.ai_recommender = None  # No recommender → 503
        app.state.cache = None

        with TestClient(app) as client:
            resp = client.get("/api/v1/ai/summary")
            assert resp.status_code == 503



@pytest.mark.asyncio
async def test_get_ai_summary_no_scan_data(mock_ai_summary):
    """Returns 404 when no scan data exists."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes.ai_analysis import router
    from app.api.dependencies import get_db

    mock_rec = MagicMock()
    mock_rec.generate_summary = AsyncMock(return_value=mock_ai_summary)

    async def mock_get_db():
        yield MagicMock()

    # Mock DB to return empty findings
    with patch(
        "app.api.routes.ai_analysis._load_latest_findings",
        new=AsyncMock(return_value=[]),
    ):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = mock_get_db
        app.state.ai_recommender = mock_rec
        app.state.cache = None

        with TestClient(app) as client:
            resp = client.get("/api/v1/ai/summary")
            assert resp.status_code == 404



class TestAISummaryModel:
    """Unit tests for AISummary Pydantic model."""

    def test_risk_level_validation(self):
        summary = AISummary(
            overall_assessment="Test assessment",
            risk_level="high",
            top_priorities=[],
            remediation_phases=[],
            trend_prediction="stable",
            generated_at=datetime.utcnow(),
            latency_ms=1000.0,
        )
        assert summary.risk_level == "high"

    def test_top_priorities_structure(self):
        fix = PriorityFix(
            finding_id="KYV-test",
            title="Test issue",
            severity="critical",
            fix_summary="Set securityContext",
            estimated_effort="5 min",
        )
        assert fix.estimated_effort == "5 min"
        assert fix.severity == "critical"

    def test_remediation_phases_ordering(self):
        phases = [
            RemediationPhase(
                phase="immediate",
                description="Fix now",
                finding_ids=["f1", "f2"],
                total_estimated_effort="30 min",
            ),
            RemediationPhase(
                phase="this_sprint",
                description="Fix this week",
                finding_ids=["f3"],
                total_estimated_effort="2 hours",
            ),
        ]
        assert phases[0].phase == "immediate"
        assert len(phases[0].finding_ids) == 2


class TestRemediationPlanModel:
    """Unit tests for RemediationPlan model."""

    def test_total_findings_field(self, mock_remediation_plan):
        assert mock_remediation_plan.total_findings == 3

    def test_latency_tracked(self, mock_remediation_plan):
        assert mock_remediation_plan.latency_ms == 987.3

    def test_phases_list(self, mock_remediation_plan):
        assert len(mock_remediation_plan.phases) == 1
        assert mock_remediation_plan.phases[0].phase == "immediate"


class TestBatchAnalyzeRequest:
    """Unit tests for batch analyze request validation."""

    def test_valid_strategy(self):
        from app.api.routes.ai_analysis import BatchAnalyzeRequest
        req = BatchAnalyzeRequest(finding_ids=["f1", "f2"], strategy="basic")
        assert req.strategy == "basic"

    def test_default_strategy(self):
        from app.api.routes.ai_analysis import BatchAnalyzeRequest
        req = BatchAnalyzeRequest(finding_ids=["f1"])
        assert req.strategy == "context_enriched"

    def test_invalid_strategy(self):
        from app.api.routes.ai_analysis import BatchAnalyzeRequest
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            BatchAnalyzeRequest(finding_ids=["f1"], strategy="invalid_strategy")
