"""
Pytest fixtures và test configuration.

Fixtures:
  - sample_policy_report: PolicyReport CRD fixture data
  - sample_vuln_report:   VulnerabilityReport CRD fixture data
  - sample_kubebench:     kube-bench JSON fixture data
  - mock_k8s_client:      Mock Kubernetes API client
  - mock_cache:           FakeRedis cache instance
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis as fake_aioredis
import pytest

from app.cache import ComplianceCache
from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    K8sResource,
    Severity,
    UnifiedComplianceFinding,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixture data loaders
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_policy_report() -> dict:
    """Load Kyverno PolicyReport sample fixture."""
    with open(FIXTURES_DIR / "policyreport-sample.json") as f:
        return json.load(f)


@pytest.fixture
def sample_vuln_report() -> dict:
    """Load Trivy VulnerabilityReport sample fixture."""
    with open(FIXTURES_DIR / "vulnerabilityreport-sample.json") as f:
        return json.load(f)


@pytest.fixture
def sample_kubebench() -> dict:
    """Load kube-bench sample fixture."""
    with open(FIXTURES_DIR / "kubebench-sample.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Mock Kubernetes client
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes ApiClient."""
    client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# Mock Redis cache (fakeredis)
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_cache() -> AsyncGenerator[ComplianceCache, None]:
    """
    FakeRedis-backed ComplianceCache for testing.
    No real Redis needed.
    """
    fake_redis = fake_aioredis.FakeRedis(decode_responses=True)

    cache = ComplianceCache(redis_url="redis://localhost:6379/0")
    cache._redis = fake_redis  # Override with fake

    yield cache

    await fake_redis.aclose()


# ---------------------------------------------------------------------------
# Sample findings
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_kyverno_finding() -> UnifiedComplianceFinding:
    return UnifiedComplianceFinding(
        finding_id="KYV-require-run-as-non-root-abc12345",
        source="kyverno",
        category=ComplianceCategory.WORKLOAD_SECURITY,
        severity=Severity.HIGH,
        status=FindingStatus.FAIL,
        resource=K8sResource(kind="Deployment", name="web-api", namespace="compliance-test"),
        title="Policy violation: require-run-as-non-root",
        description="Container must not run as root. Set runAsNonRoot: true.",
    )


@pytest.fixture
def sample_trivy_finding() -> UnifiedComplianceFinding:
    return UnifiedComplianceFinding(
        finding_id="TRV-CVE-2024-38428-web-api-def67890",
        source="trivy",
        category=ComplianceCategory.SUPPLY_CHAIN,
        severity=Severity.CRITICAL,
        status=FindingStatus.FAIL,
        resource=K8sResource(kind="Deployment", name="web-api", namespace="compliance-test"),
        title="Vulnerability: CVE-2024-38428",
        description="wget: Misinterpretation of input may lead to improper behavior",
    )


@pytest.fixture
def sample_kubebench_finding() -> UnifiedComplianceFinding:
    return UnifiedComplianceFinding(
        finding_id="CIS-1.2.1",
        source="kube-bench",
        category=ComplianceCategory.CLUSTER_SECURITY,
        severity=Severity.CRITICAL,
        status=FindingStatus.FAIL,
        resource=K8sResource(kind="Node", name="cluster", namespace=None),
        title="CIS 1.2.1: Ensure that the --anonymous-auth argument is set to false",
        description="API server allows anonymous authentication",
    )


@pytest.fixture
def mixed_findings(
    sample_kyverno_finding,
    sample_trivy_finding,
    sample_kubebench_finding,
) -> list[UnifiedComplianceFinding]:
    """A mix of findings from all 3 sources."""
    return [sample_kyverno_finding, sample_trivy_finding, sample_kubebench_finding]
