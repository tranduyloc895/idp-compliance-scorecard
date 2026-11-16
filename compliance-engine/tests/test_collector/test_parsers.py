"""Kiểm tra parser kube-bench (dict/list) và khóa dedup/ID của Trivy."""

from __future__ import annotations

from app.collector.aggregator import ComplianceAggregator
from app.collector.kubebench import KubeBenchCollector
from app.models.finding import RawFinding
from app.normalizer.mapper import NormalizerMapper


def _bench_collector() -> KubeBenchCollector:
    # Parser không gọi API, nên không cần ApiClient thật.
    return KubeBenchCollector.__new__(KubeBenchCollector)


def _controls(test_number: str) -> dict:
    return {
        "Controls": [
            {
                "id": "4",
                "tests": [{"section": "4.1", "results": [{"test_number": test_number, "status": "FAIL"}]}],
            }
        ]
    }


def test_kubebench_parses_dict_output():
    findings = _bench_collector()._parse_results(_controls("4.1.1"))
    assert [f.raw_data["test_number"] for f in findings] == ["4.1.1"]


def test_kubebench_parses_list_output_from_multiple_nodes():
    findings = _bench_collector()._parse_results([_controls("4.1.1"), _controls("4.2.1")])
    assert sorted(f.raw_data["test_number"] for f in findings) == ["4.1.1", "4.2.1"]


def test_kubebench_ignores_unexpected_type():
    assert _bench_collector()._parse_results("not-json-object") == []  # type: ignore[arg-type]


def _trivy(namespace: str, container: str, package: str) -> RawFinding:
    return RawFinding(
        source="trivy",
        raw_data={
            "vulnerability_id": "CVE-2024-0001",
            "resource_kind": "ReplicaSet",
            "resource_name": "web",
            "resource_namespace": namespace,
            "container_name": container,
            "package": package,
            "installed_version": "1.0",
            "severity": "high",
        },
    )


def test_trivy_dedup_keeps_distinct_namespace_container_package():
    agg = ComplianceAggregator.__new__(ComplianceAggregator)
    findings = [
        _trivy("ns-a", "app", "openssl"),
        _trivy("ns-b", "app", "openssl"),  # khác namespace
        _trivy("ns-a", "sidecar", "openssl"),  # khác container
        _trivy("ns-a", "app", "libssl3"),  # khác package
        _trivy("ns-a", "app", "openssl"),  # trùng hoàn toàn -> bị loại
    ]
    assert len(agg._deduplicate(findings)) == 4


def test_trivy_finding_ids_are_unique_per_container_and_package():
    mapper = NormalizerMapper()
    ids = {
        mapper.normalize(_trivy("ns-a", "app", "openssl")).finding_id,
        mapper.normalize(_trivy("ns-a", "sidecar", "openssl")).finding_id,
        mapper.normalize(_trivy("ns-a", "app", "libssl3")).finding_id,
        mapper.normalize(_trivy("ns-b", "app", "openssl")).finding_id,
    }
    assert len(ids) == 4
