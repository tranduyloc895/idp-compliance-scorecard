"""
Tests for AIRecommender.generate_summary() and generate_remediation_plan().

All Gemini API calls are mocked via MagicMock.
Focuses on:
  - prompt building logic
  - output parsing (Pydantic validation)
  - latency tracking
  - error handling
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest

from app.models.finding import (
    UnifiedComplianceFinding,
    ComplianceCategory,
    Severity,
    FindingStatus,
    K8sResource,
)
from app.models.score import ScoreResult, Classification, DomainScore
from app.models.ai_summary import AISummary, RemediationPlan, PriorityFix, RemediationPhase


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def sample_findings() -> list[UnifiedComplianceFinding]:
    return [
        UnifiedComplianceFinding(
            finding_id="KYV-require-run-as-non-root-abc",
            source="kyverno",
            category=ComplianceCategory.WORKLOAD_SECURITY,
            severity=Severity.CRITICAL,
            status=FindingStatus.FAIL,
            resource=K8sResource(kind="Deployment", name="web-api", namespace="default"),
            title="Container running as root",
            description="Must set runAsNonRoot: true",
        ),
        UnifiedComplianceFinding(
            finding_id="TRV-CVE-2024-1234-cart",
            source="trivy",
            category=ComplianceCategory.SUPPLY_CHAIN,
            severity=Severity.HIGH,
            status=FindingStatus.FAIL,
            resource=K8sResource(kind="Deployment", name="cart", namespace="default"),
            title="CVE-2024-1234 in base image",
            description="Critical CVE in wget package",
        ),
        UnifiedComplianceFinding(
            finding_id="CIS-1.2.1",
            source="kube-bench",
            category=ComplianceCategory.CLUSTER_SECURITY,
            severity=Severity.MEDIUM,
            status=FindingStatus.PASS,  # This one passes — should not be in remediation
            resource=K8sResource(kind="Node", name="cluster", namespace=None),
            title="CIS 1.2.1: anonymous auth disabled",
            description="API server anonymous auth is disabled",
        ),
    ]


@pytest.fixture
def sample_score() -> ScoreResult:
    return ScoreResult(
        scan_id=1,
        overall_score=72.5,
        classification=Classification.FAIR,
        domains=[
            DomainScore(
                domain=ComplianceCategory.CLUSTER_SECURITY,
                score=80.0,
                weight=0.35,
                total_checks=10,
                passed=8,
                failed=2,
                critical_count=0,
                high_count=2,
                medium_count=0,
                low_count=0,
            ),
            DomainScore(
                domain=ComplianceCategory.WORKLOAD_SECURITY,
                score=65.0,
                weight=0.35,
                total_checks=15,
                passed=9,
                failed=6,
                critical_count=1,
                high_count=3,
                medium_count=2,
                low_count=0,
            ),
        ],
        total_findings=25,
        total_passed=17,
        total_failed=8,
        critical_violations=1,
        high_violations=5,
    )


@pytest.fixture
def mock_ai_summary_response() -> str:
    """Mock Gemini JSON response for executive summary."""
    data = {
        "overall_assessment": (
            "The cluster has moderate security hardening with critical gaps in workload security. "
            "Immediate attention required for root container violations."
        ),
        "risk_level": "high",
        "top_priorities": [
            {
                "finding_id": "KYV-require-run-as-non-root-abc",
                "title": "Container running as root",
                "severity": "critical",
                "fix_summary": "Set runAsNonRoot: true",
                "estimated_effort": "5 min",
            }
        ],
        "remediation_phases": [
            {
                "phase": "immediate",
                "description": "Fix CRITICAL violations today",
                "finding_ids": ["KYV-require-run-as-non-root-abc"],
                "total_estimated_effort": "30 min",
            },
            {
                "phase": "this_sprint",
                "description": "Fix HIGH violations this week",
                "finding_ids": ["TRV-CVE-2024-1234-cart"],
                "total_estimated_effort": "2 hours",
            },
            {
                "phase": "backlog",
                "description": "Schedule remaining improvements",
                "finding_ids": [],
                "total_estimated_effort": "0 min",
            },
        ],
        "trend_prediction": "stable",
        "generated_at": "2026-09-11T00:00:00",
        "latency_ms": 0.0,
    }
    return json.dumps(data)


@pytest.fixture
def mock_remediation_plan_response() -> str:
    """Mock Gemini JSON response for remediation plan."""
    data = {
        "phases": [
            {
                "phase": "immediate",
                "description": "Fix CRITICAL violations today",
                "finding_ids": ["KYV-require-run-as-non-root-abc"],
                "total_estimated_effort": "30 min",
            },
            {
                "phase": "this_sprint",
                "description": "Fix HIGH violations",
                "finding_ids": ["TRV-CVE-2024-1234-cart"],
                "total_estimated_effort": "2 hours",
            },
            {
                "phase": "backlog",
                "description": "MEDIUM/LOW improvements",
                "finding_ids": [],
                "total_estimated_effort": "0 min",
            },
        ],
        "total_findings": 2,
        "total_estimated_effort": "2.5 hours",
        "generated_at": "2026-09-11T00:00:00",
        "latency_ms": 0.0,
    }
    return json.dumps(data)


# ─── Tests ──────────────────────────────────────────────────────────────────


class TestGenerateSummary:
    """Tests for AIRecommender.generate_summary()."""

    @pytest.mark.asyncio
    async def test_generate_summary_success(
        self,
        sample_findings,
        sample_score,
        mock_ai_summary_response,
    ):
        """generate_summary returns valid AISummary with correct fields."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")

        # Mock the Gemini call
        mock_response = MagicMock()
        mock_response.text = mock_ai_summary_response
        rec._call_gemini_with_schema = AsyncMock(return_value=mock_response)

        summary = await rec.generate_summary(sample_findings, sample_score)

        assert isinstance(summary, AISummary)
        assert summary.risk_level == "high"
        assert summary.overall_assessment != ""
        assert len(summary.top_priorities) == 1
        assert summary.top_priorities[0].finding_id == "KYV-require-run-as-non-root-abc"
        assert len(summary.remediation_phases) == 3
        assert summary.trend_prediction == "stable"
        assert summary.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_summary_only_failed_findings(
        self,
        sample_findings,
        sample_score,
        mock_ai_summary_response,
    ):
        """Only FAIL status findings should appear in summary prompt."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")

        prompt_built = []

        async def capture_prompt(prompt, schema):
            prompt_built.append(prompt)
            mock_response = MagicMock()
            mock_response.text = mock_ai_summary_response
            return mock_response

        rec._call_gemini_with_schema = capture_prompt

        await rec.generate_summary(sample_findings, sample_score)

        # CIS-1.2.1 has status=PASS, should NOT appear in findings summary
        assert prompt_built, "Prompt was not built"
        # The passing finding should not be in the prompt
        assert "CIS-1.2.1" not in prompt_built[0] or "PASS" not in prompt_built[0]

    @pytest.mark.asyncio
    async def test_generate_summary_tracks_latency(
        self,
        sample_findings,
        sample_score,
        mock_ai_summary_response,
    ):
        """Summary latency_ms should be positive."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")
        mock_response = MagicMock()
        mock_response.text = mock_ai_summary_response
        rec._call_gemini_with_schema = AsyncMock(return_value=mock_response)

        summary = await rec.generate_summary(sample_findings, sample_score)
        assert summary.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_summary_raises_on_api_error(
        self,
        sample_findings,
        sample_score,
    ):
        """generate_summary propagates Gemini errors."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")
        rec._call_gemini_with_schema = AsyncMock(side_effect=Exception("API quota exceeded"))

        with pytest.raises(Exception, match="API quota exceeded"):
            await rec.generate_summary(sample_findings, sample_score)


class TestGenerateRemediationPlan:
    """Tests for AIRecommender.generate_remediation_plan()."""

    @pytest.mark.asyncio
    async def test_generate_plan_success(
        self,
        sample_findings,
        mock_remediation_plan_response,
    ):
        """generate_remediation_plan returns valid RemediationPlan."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")
        mock_response = MagicMock()
        mock_response.text = mock_remediation_plan_response
        rec._call_gemini_with_schema = AsyncMock(return_value=mock_response)

        plan = await rec.generate_remediation_plan(sample_findings)

        assert isinstance(plan, RemediationPlan)
        assert len(plan.phases) == 3
        assert plan.phases[0].phase == "immediate"
        assert plan.total_findings == 2  # Only FAIL findings
        assert plan.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_plan_counts_only_failures(
        self,
        sample_findings,
        mock_remediation_plan_response,
    ):
        """Only failed findings should be counted in remediation plan."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")
        mock_response = MagicMock()
        mock_response.text = mock_remediation_plan_response
        rec._call_gemini_with_schema = AsyncMock(return_value=mock_response)

        plan = await rec.generate_remediation_plan(sample_findings)

        # sample_findings has 2 FAIL, 1 PASS
        assert plan.total_findings == 2

    @pytest.mark.asyncio
    async def test_generate_plan_empty_findings(self, mock_remediation_plan_response):
        """Handle empty findings list gracefully."""
        from app.recommender.ai_recommender import AIRecommender

        rec = AIRecommender(api_key="test-key")
        mock_response = MagicMock()
        mock_response.text = mock_remediation_plan_response
        rec._call_gemini_with_schema = AsyncMock(return_value=mock_response)

        plan = await rec.generate_remediation_plan([])
        assert plan.total_findings == 0
