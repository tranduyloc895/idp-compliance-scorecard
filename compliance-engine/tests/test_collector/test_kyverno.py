"""
Tests cho KyvernoCollector.

Mock K8s CustomObjectsApi để test offline (không cần cluster).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collector.kyverno import KyvernoCollector
from app.models.finding import RawFinding


@pytest.fixture
def mock_kyverno_api_response(sample_policy_report):
    """Mock CustomObjectsApi response với sample PolicyReport."""
    return {"items": [sample_policy_report]}


@pytest.fixture
def kyverno_collector(mock_k8s_client):
    """KyvernoCollector với mock K8s client."""
    with patch("app.collector.kyverno.CustomObjectsApi") as mock_api_class:
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        collector = KyvernoCollector(mock_k8s_client)
        collector.custom_api = mock_api
        return collector, mock_api


@pytest.mark.asyncio
async def test_collect_namespace_findings(kyverno_collector, mock_kyverno_api_response):
    """Test collect() trả về RawFindings từ PolicyReport."""
    collector, mock_api = kyverno_collector
    mock_api.list_namespaced_custom_object = AsyncMock(return_value=mock_kyverno_api_response)
    mock_api.list_cluster_custom_object = AsyncMock(return_value={"items": []})

    findings = await collector.collect(namespace="compliance-test")

    assert len(findings) > 0
    assert all(isinstance(f, RawFinding) for f in findings)
    assert all(f.source == "kyverno" for f in findings)


@pytest.mark.asyncio
async def test_extract_findings_count(kyverno_collector, sample_policy_report):
    """Test số lượng findings extracted từ 8-result PolicyReport."""
    collector, _ = kyverno_collector
    findings = collector._extract_findings_from_report(sample_policy_report)

    # sample_policy_report có 8 results
    assert len(findings) == 8


@pytest.mark.asyncio
async def test_extract_findings_fields(kyverno_collector, sample_policy_report):
    """Test các trường trong RawFinding được extract đúng."""
    collector, _ = kyverno_collector
    findings = collector._extract_findings_from_report(sample_policy_report)

    # Tìm finding FAIL đầu tiên (disallow-privilege-escalation)
    fail_findings = [f for f in findings if f.raw_data.get("result") == "fail"]
    assert len(fail_findings) == 5  # 5 fail results trong sample

    first_fail = fail_findings[0]
    assert first_fail.raw_data["policy"] == "disallow-privilege-escalation"
    assert first_fail.raw_data["result"] == "fail"
    assert first_fail.raw_data["severity"] == "high"


@pytest.mark.asyncio
async def test_collect_returns_empty_on_api_error(kyverno_collector):
    """Test collector không raise exception khi K8s API fail."""
    collector, mock_api = kyverno_collector
    mock_api.list_namespaced_custom_object = AsyncMock(side_effect=Exception("K8s API error"))
    mock_api.list_cluster_custom_object = AsyncMock(side_effect=Exception("K8s API error"))

    # Should not raise, return empty list
    findings = await collector.collect(namespace="test")
    assert findings == []
