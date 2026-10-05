"""
Tests cho Normalizer — schema + mapper.

Test các transform functions và full mapping pipeline.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    RawFinding,
    Severity,
)
from app.normalizer.mapper import NormalizerMapper
from app.normalizer.schema import (
    get_kubebench_category,
    get_kyverno_category_severity,
    get_trivy_severity,
    normalize_status_from_kyverno,
)


# ---------------------------------------------------------------------------
# Schema transform functions
# ---------------------------------------------------------------------------


class TestKyvernoPolicyMap:
    def test_known_policy_maps_correctly(self):
        category, severity = get_kyverno_category_severity("require-run-as-non-root")
        assert category == ComplianceCategory.WORKLOAD_SECURITY
        assert severity == Severity.HIGH

    def test_disallow_latest_tag_is_supply_chain(self):
        category, severity = get_kyverno_category_severity("disallow-latest-tag")
        assert category == ComplianceCategory.SUPPLY_CHAIN
        assert severity == Severity.HIGH

    def test_require_labels_is_platform_config(self):
        category, severity = get_kyverno_category_severity("require-labels")
        assert category == ComplianceCategory.PLATFORM_CONFIG
        assert severity == Severity.LOW

    def test_partial_match(self):
        """Policy name với prefix như 'cpol-require-run-as-non-root'"""
        category, severity = get_kyverno_category_severity("cpol-require-run-as-non-root")
        assert category == ComplianceCategory.WORKLOAD_SECURITY

    def test_unknown_policy_returns_default(self):
        category, severity = get_kyverno_category_severity("custom-unknown-policy-xyz")
        assert category == ComplianceCategory.WORKLOAD_SECURITY  # default
        assert severity == Severity.MEDIUM  # default


class TestTrivirySeverityMap:
    def test_critical(self):
        assert get_trivy_severity("CRITICAL") == Severity.CRITICAL

    def test_high(self):
        assert get_trivy_severity("HIGH") == Severity.HIGH

    def test_case_insensitive(self):
        assert get_trivy_severity("critical") == Severity.CRITICAL
        assert get_trivy_severity("Medium") == Severity.MEDIUM

    def test_unknown_returns_info(self):
        assert get_trivy_severity("UNKNOWN") == Severity.INFO


class TestKubebenchCategoryMap:
    def test_section_1_is_cluster_security(self):
        assert get_kubebench_category("1.2.1") == ComplianceCategory.CLUSTER_SECURITY

    def test_section_4_is_workload_security(self):
        assert get_kubebench_category("4.2.1") == ComplianceCategory.WORKLOAD_SECURITY

    def test_section_5_is_platform_config(self):
        assert get_kubebench_category("5.1.6") == ComplianceCategory.PLATFORM_CONFIG


# ---------------------------------------------------------------------------
# NormalizerMapper — full pipeline
# ---------------------------------------------------------------------------


class TestNormalizerMapper:
    @pytest.fixture
    def mapper(self):
        return NormalizerMapper()

    def test_normalize_kyverno_finding(self, mapper):
        raw = RawFinding(
            source="kyverno",
            raw_data={
                "policy": "require-run-as-non-root",
                "rule": "run-as-non-root",
                "result": "fail",
                "severity": "high",
                "message": "Container must not run as root",
                "resource_kind": "Deployment",
                "resource_name": "web-api",
                "resource_namespace": "compliance-test",
                "is_cluster_scoped": False,
                "timestamp": {},
            },
        )

        finding = mapper.normalize(raw)

        assert finding is not None
        assert finding.source == "kyverno"
        assert finding.category == ComplianceCategory.WORKLOAD_SECURITY
        assert finding.severity == Severity.HIGH
        assert finding.status == FindingStatus.FAIL
        assert finding.resource.kind == "Deployment"
        assert finding.resource.namespace == "compliance-test"
        assert finding.finding_id.startswith("KYV-")

    def test_normalize_trivy_finding(self, mapper):
        raw = RawFinding(
            source="trivy",
            raw_data={
                "vulnerability_id": "CVE-2024-38428",
                "resource_name": "web-api",
                "resource_kind": "Deployment",
                "resource_namespace": "compliance-test",
                "container_name": "api",
                "image": "nginx:1.24.0",
                "package": "wget",
                "installed_version": "1.21.3",
                "fixed_version": "1.21.4",
                "severity": "critical",
                "title": "wget: Misinterpretation of input",
                "description": "CVE description here",
                "primary_link": "https://nvd.nist.gov",
                "score": 9.8,
                "summary": {},
            },
        )

        finding = mapper.normalize(raw)

        assert finding is not None
        assert finding.source == "trivy"
        assert finding.category == ComplianceCategory.SUPPLY_CHAIN
        assert finding.severity == Severity.CRITICAL
        assert finding.status == FindingStatus.FAIL
        assert finding.finding_id.startswith("TRV-")

    def test_normalize_kubebench_finding(self, mapper):
        raw = RawFinding(
            source="kube-bench",
            raw_data={
                "test_number": "1.2.1",
                "test_desc": "Ensure anonymous-auth is false",
                "status": "FAIL",
                "severity": "critical",
                "category": "cluster_security",
                "remediation": "Set --anonymous-auth=false",
                "actual_value": "true",
                "scored": True,
                "expected_result": "false",
                "resource_kind": "Node",
                "resource_name": "cluster",
                "resource_namespace": None,
            },
        )

        finding = mapper.normalize(raw)

        assert finding is not None
        assert finding.source == "kube-bench"
        assert finding.finding_id == "CIS-1.2.1"
        assert finding.category == ComplianceCategory.CLUSTER_SECURITY
        assert finding.severity == Severity.CRITICAL
        assert finding.status == FindingStatus.FAIL
        assert finding.resource.namespace is None  # Cluster-scoped

    def test_normalize_all_returns_only_valid(self, mapper):
        """normalize_all() bỏ qua findings không normalize được."""
        valid_raw = RawFinding(
            source="kube-bench",
            raw_data={
                "test_number": "1.2.1",
                "test_desc": "Test",
                "status": "FAIL",
                "severity": "high",
                "category": "cluster_security",
                "remediation": "",
                "actual_value": "",
                "scored": True,
                "expected_result": "",
                "resource_kind": "Node",
                "resource_name": "cluster",
                "resource_namespace": None,
            },
        )
        invalid_raw = RawFinding(
            source="unknown_source",  # type: ignore
            raw_data={"bad": "data"},
        )

        results = mapper.normalize_all([valid_raw, invalid_raw])
        assert len(results) == 1
