"""
Tests cho RuleBasedRecommender.

Verify rule matching logic và template loading.
"""

from __future__ import annotations

import pytest

from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    K8sResource,
    Severity,
    UnifiedComplianceFinding,
)
from app.recommender.rules import RuleBasedRecommender


def make_finding_with_id(finding_id: str, title: str = "Test") -> UnifiedComplianceFinding:
    return UnifiedComplianceFinding(
        finding_id=finding_id,
        source="kyverno",
        category=ComplianceCategory.WORKLOAD_SECURITY,
        severity=Severity.HIGH,
        status=FindingStatus.FAIL,
        resource=K8sResource(kind="Deployment", name="web-api", namespace="default"),
        title=title,
        description="Test description",
    )


class TestRuleBasedRecommender:
    @pytest.fixture
    def recommender(self):
        return RuleBasedRecommender()

    def test_matches_run_as_non_root_by_finding_id(self, recommender):
        finding = make_finding_with_id("KYV-require-run-as-non-root-abc12345")
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert rec.rule_id == "WS-001"
        assert "runAsNonRoot" in rec.yaml_fix

    def test_matches_disallow_latest_tag(self, recommender):
        finding = make_finding_with_id("KYV-disallow-latest-tag-def67890")
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert rec.rule_id == "SC-001"

    def test_matches_by_title_keyword(self, recommender):
        finding = make_finding_with_id(
            "KYV-unknown-policy-xyz123",
            title="Container runs as root",
        )
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert rec.rule_id == "WS-001"

    def test_returns_none_for_unknown_finding(self, recommender):
        finding = make_finding_with_id("UNKNOWN-completely-unknown-policy-abc")
        rec = recommender.get_recommendation(finding)
        assert rec is None

    def test_yaml_fix_is_not_empty(self, recommender):
        finding = make_finding_with_id("KYV-require-resource-limits-abc12345")
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert len(rec.yaml_fix) > 0
        # Template should contain 'resources' keyword
        assert "resources" in rec.yaml_fix.lower() or "limits" in rec.yaml_fix.lower()

    def test_reference_is_populated(self, recommender):
        finding = make_finding_with_id("KYV-drop-all-capabilities-abc12345")
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert "CIS" in rec.reference

    def test_cis_1_2_1_matches(self, recommender):
        finding = make_finding_with_id("CIS-1.2.1", title="CIS 1.2.1: anonymous-auth is true")
        rec = recommender.get_recommendation(finding)
        assert rec is not None
        assert rec.rule_id == "CS-001"

    def test_coverage_stats(self, recommender):
        stats = recommender.get_coverage_stats()
        assert stats["total_rules"] >= 10
        assert stats["categories"]["workload_security"] > 0
        assert stats["categories"]["supply_chain"] > 0
