"""
KyvernoCollector — Đọc PolicyReport + ClusterPolicyReport CRDs từ Kubernetes API.

Kyverno tự động tạo PolicyReport trong mỗi namespace sau khi evaluate policies.
ClusterPolicyReport cho cluster-scoped resources.

API endpoint:
  - /apis/wgpolicyk8s.io/v1alpha2/namespaces/{ns}/policyreports
  - /apis/wgpolicyk8s.io/v1alpha2/clusterpolicyreports
"""

from __future__ import annotations

import logging
from typing import Optional

from kubernetes_asyncio.client import ApiClient, CustomObjectsApi

from app.collector.base import BaseCollector
from app.models.finding import RawFinding

logger = logging.getLogger(__name__)

# Kyverno PolicyReport API group
POLICY_REPORT_GROUP = "wgpolicyk8s.io"
POLICY_REPORT_VERSION = "v1alpha2"
POLICY_REPORT_PLURAL = "policyreports"
CLUSTER_POLICY_REPORT_PLURAL = "clusterpolicyreports"


class KyvernoCollector(BaseCollector):
    """
    Collector cho Kyverno PolicyReport CRDs.

    Đọc tất cả PolicyReport trong cluster (hoặc 1 namespace cụ thể),
    extract từng result entry thành RawFinding để normalizer xử lý.
    """

    def __init__(self, k8s_client: ApiClient) -> None:
        super().__init__(k8s_client)
        self.custom_api = CustomObjectsApi(k8s_client)

    async def collect(self, namespace: Optional[str] = None) -> list[RawFinding]:
        """
        Collect PolicyReports.

        Returns:
            list[RawFinding] với source="kyverno"
        """
        findings: list[RawFinding] = []

        try:
            # 1. Namespace-scoped PolicyReports
            if namespace:
                reports = await self._get_namespace_reports(namespace)
            else:
                reports = await self._get_all_namespace_reports()

            for report in reports:
                findings.extend(self._extract_findings_from_report(report))

            # 2. Cluster-scoped ClusterPolicyReports (luôn lấy, không filter namespace)
            cluster_reports = await self._get_cluster_reports()
            for report in cluster_reports:
                findings.extend(self._extract_findings_from_report(report, is_cluster_scoped=True))

            logger.info(
                "KyvernoCollector: collected %d findings from %d namespace reports + %d cluster reports",
                len(findings),
                len(reports),
                len(cluster_reports),
            )

        except Exception as e:
            logger.error("KyvernoCollector error: %s", e, exc_info=True)

        return findings

    async def _get_namespace_reports(self, namespace: str) -> list[dict]:
        """Lấy PolicyReports trong 1 namespace cụ thể."""
        try:
            response = await self.custom_api.list_namespaced_custom_object(
                group=POLICY_REPORT_GROUP,
                version=POLICY_REPORT_VERSION,
                namespace=namespace,
                plural=POLICY_REPORT_PLURAL,
            )
            return response.get("items", [])
        except Exception as e:
            logger.warning("Failed to get PolicyReports in namespace %s: %s", namespace, e)
            return []

    async def _get_all_namespace_reports(self) -> list[dict]:
        """Lấy tất cả PolicyReports trong cluster."""
        try:
            response = await self.custom_api.list_cluster_custom_object(
                group=POLICY_REPORT_GROUP,
                version=POLICY_REPORT_VERSION,
                plural=POLICY_REPORT_PLURAL,
            )
            return response.get("items", [])
        except Exception as e:
            logger.warning("Failed to get all PolicyReports: %s", e)
            return []

    async def _get_cluster_reports(self) -> list[dict]:
        """Lấy ClusterPolicyReports (cluster-scoped resources)."""
        try:
            response = await self.custom_api.list_cluster_custom_object(
                group=POLICY_REPORT_GROUP,
                version=POLICY_REPORT_VERSION,
                plural=CLUSTER_POLICY_REPORT_PLURAL,
            )
            return response.get("items", [])
        except Exception as e:
            logger.warning("Failed to get ClusterPolicyReports: %s", e)
            return []

    def _extract_findings_from_report(
        self, report: dict, is_cluster_scoped: bool = False
    ) -> list[RawFinding]:
        """
        Parse PolicyReport → list[RawFinding].

        Mỗi entry trong report.results[] trở thành 1 RawFinding.
        """
        findings = []
        results = report.get("results", [])
        metadata = report.get("metadata", {})
        scope = report.get("scope", {})

        namespace = metadata.get("namespace") if not is_cluster_scoped else None

        for result in results:
            # Xác định resource từ scope hoặc từ result.resources[]
            resource_info = scope or {}
            if result.get("resources") and len(result["resources"]) > 0:
                resource_info = result["resources"][0]

            raw_finding = RawFinding(
                source="kyverno",
                raw_data={
                    "policy": result.get("policy", "unknown"),
                    "rule": result.get("rule", ""),
                    "result": result.get("result", "fail"),  # "pass" | "fail" | "warn"
                    "severity": result.get("severity", "medium"),
                    "message": result.get("message", ""),
                    "resource_kind": resource_info.get("kind", "Unknown"),
                    "resource_name": resource_info.get("name", "unknown"),
                    "resource_namespace": resource_info.get("namespace") or namespace,
                    "is_cluster_scoped": is_cluster_scoped,
                    "timestamp": result.get("timestamp", {}),
                },
            )
            findings.append(raw_finding)

        return findings
