"""
Tests cho ComplianceScorer — weighted scoring engine.

Verify scoring algorithm với known inputs.
Target scores từ plan:
  - workload-a-poor:      ~45-55 (Poor 🔴)
  - workload-b-excellent: ~90-95 (Excellent 🟢)
  - workload-c-fair:      ~60-70 (Fair 🟡)
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    K8sResource,
    Severity,
    UnifiedComplianceFinding,
)
from app.models.score import Classification
from app.scorer.classifier import classify_score
from app.scorer.engine import ComplianceScorer


def make_finding(
    category: ComplianceCategory,
    severity: Severity,
    status: FindingStatus,
    finding_id: str = "TEST-001",
) -> UnifiedComplianceFinding:
    """Helper để tạo finding nhanh."""
    return UnifiedComplianceFinding(
        finding_id=finding_id,
        source="kyverno",
        category=category,
        severity=severity,
        status=status,
        resource=K8sResource(kind="Deployment", name="test", namespace="default"),
        title="Test finding",
        description="Test description",
    )


class TestClassifier:
    def test_excellent(self):
        assert classify_score(95.0) == Classification.EXCELLENT
        assert classify_score(90.0) == Classification.EXCELLENT

    def test_good(self):
        assert classify_score(85.0) == Classification.GOOD
        assert classify_score(75.0) == Classification.GOOD

    def test_fair(self):
        assert classify_score(70.0) == Classification.FAIR
        assert classify_score(60.0) == Classification.FAIR

    def test_poor(self):
        assert classify_score(59.9) == Classification.POOR
        assert classify_score(0.0) == Classification.POOR


class TestComplianceScorer:
    @pytest.fixture
    def scorer(self):
        return ComplianceScorer()

    def test_perfect_score_no_findings(self, scorer):
        """No findings → score 100.0 Excellent."""
        result = scorer.calculate([], scan_id=1)
        assert result.overall_score == 100.0
        assert result.classification == Classification.EXCELLENT

    def test_all_pass_findings(self, scorer):
        """All PASS findings → high score."""
        findings = [
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.PASS, f"F-{i}")
            for i in range(10)
        ]
        result = scorer.calculate(findings, scan_id=1)
        assert result.overall_score >= 90.0
        assert result.classification == Classification.EXCELLENT

    def test_critical_penalty_reduces_score(self, scorer):
        """CRITICAL FAIL findings penalize score heavily (-15 each)."""
        # 1 pass, 2 critical fail
        findings = [
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.CRITICAL, FindingStatus.FAIL, "F-1"),
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.CRITICAL, FindingStatus.FAIL, "F-2"),
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.LOW, FindingStatus.PASS, "F-3"),
        ]
        result = scorer.calculate(findings, scan_id=1)
        # base = 1/3 * 100 = 33.3, penalty = 2*15 = 30, domain_score = max(3.3, 0) * 0.35 weighted
        ws_domain = result.get_domain(ComplianceCategory.WORKLOAD_SECURITY)
        assert ws_domain is not None
        assert ws_domain.critical_count == 2
        assert ws_domain.score < 50.0

    def test_score_bounded_0_100(self, scorer):
        """Score không vượt ra ngoài [0, 100]."""
        # Many critical fails
        findings = [
            make_finding(ComplianceCategory.CLUSTER_SECURITY, Severity.CRITICAL, FindingStatus.FAIL, f"F-{i}")
            for i in range(20)
        ]
        result = scorer.calculate(findings, scan_id=1)
        assert 0.0 <= result.overall_score <= 100.0

    def test_poor_workload_simulation(self, scorer):
        """
        Simulate workload-a-poor: target ~45-55.

        5 violations: no securityContext, no limits, :latest tag,
        no probes, allowPrivilegeEscalation
        """
        findings = [
            # Workload Security failures (CRITICAL + HIGH)
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.FAIL, "WS-1"),  # no runAsNonRoot
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.FAIL, "WS-2"),  # privilege escalation
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.MEDIUM, FindingStatus.FAIL, "WS-3"),  # no readOnly
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.FAIL, "WS-4"),  # capabilities
            # Supply Chain failures
            make_finding(ComplianceCategory.SUPPLY_CHAIN, Severity.HIGH, FindingStatus.FAIL, "SC-1"),  # :latest tag
            # Platform Config failures
            make_finding(ComplianceCategory.PLATFORM_CONFIG, Severity.MEDIUM, FindingStatus.FAIL, "PC-1"),  # no limits
            make_finding(ComplianceCategory.PLATFORM_CONFIG, Severity.LOW, FindingStatus.FAIL, "PC-2"),   # no labels
            make_finding(ComplianceCategory.PLATFORM_CONFIG, Severity.MEDIUM, FindingStatus.FAIL, "PC-3"),  # no probes
        ]
        result = scorer.calculate(findings, scan_id=1)
        # Target: ~45-55 based on plan
        assert result.classification == Classification.POOR
        assert result.overall_score < 60.0

    def test_excellent_workload_simulation(self, scorer):
        """
        Simulate workload-b-excellent: target ~90-95.

        All PASS findings.
        """
        findings = [
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.PASS, f"WS-{i}")
            for i in range(4)
        ] + [
            make_finding(ComplianceCategory.SUPPLY_CHAIN, Severity.HIGH, FindingStatus.PASS, "SC-1"),
            make_finding(ComplianceCategory.PLATFORM_CONFIG, Severity.MEDIUM, FindingStatus.PASS, f"PC-{i}")
            for i in range(3)
        ]
        result = scorer.calculate(findings, scan_id=1)
        assert result.overall_score >= 90.0
        assert result.classification == Classification.EXCELLENT

    def test_domain_scores_sum_to_overall(self, scorer):
        """Overall score = Σ(domain_score × weight)."""
        findings = [
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.FAIL, "F-1"),
            make_finding(ComplianceCategory.SUPPLY_CHAIN, Severity.MEDIUM, FindingStatus.PASS, "F-2"),
        ]
        result = scorer.calculate(findings, scan_id=1)

        computed = sum(d.score * d.weight for d in result.domains)
        assert abs(computed - result.overall_score) < 0.01  # floating point tolerance

    def test_counters_are_correct(self, scorer):
        """Total findings, passed, failed counters."""
        findings = [
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH, FindingStatus.FAIL, "F-1"),
            make_finding(ComplianceCategory.WORKLOAD_SECURITY, Severity.MEDIUM, FindingStatus.PASS, "F-2"),
            make_finding(ComplianceCategory.SUPPLY_CHAIN, Severity.CRITICAL, FindingStatus.FAIL, "F-3"),
        ]
        result = scorer.calculate(findings, scan_id=1)
        assert result.total_findings == 3
        assert result.total_passed == 1
        assert result.total_failed == 2
        assert result.critical_violations == 1
        assert result.high_violations == 1
