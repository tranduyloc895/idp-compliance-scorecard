"""
TrivyCollector — Đọc VulnerabilityReport CRDs từ Kubernetes API.

Trivy Operator tự động scan images và tạo VulnerabilityReport trong namespace
của mỗi workload. ConfigAuditReport cũng được đọc nếu có.

API endpoint:
  - /apis/aquasecurity.github.io/v1alpha1/vulnerabilityreports
"""

from __future__ import annotations

import logging
from typing import Optional

from kubernetes_asyncio.client import ApiClient, CustomObjectsApi

from app.collector.base import BaseCollector
from app.models.finding import RawFinding

logger = logging.getLogger(__name__)

# Trivy Operator CRD API group
TRIVY_GROUP = "aquasecurity.github.io"
TRIVY_VERSION = "v1alpha1"
VULN_REPORT_PLURAL = "vulnerabilityreports"
CONFIG_AUDIT_PLURAL = "configauditreports"


class TrivyCollector(BaseCollector):
    """
    Collector cho Trivy VulnerabilityReport CRDs.

    Đọc VulnerabilityReport, group by severity, tạo 1 RawFinding
    cho mỗi severity level có ít nhất 1 vuln (để scoring dùng severity weight).
    """

    def __init__(self, k8s_client: ApiClient) -> None:
        super().__init__(k8s_client)
        self.custom_api = CustomObjectsApi(k8s_client)

    async def collect(self, namespace: Optional[str] = None) -> list[RawFinding]:
        """
        Collect VulnerabilityReports.

        Returns:
            list[RawFinding] với source="trivy"
            Mỗi vulnerability thành 1 finding riêng để scoring chính xác.
        """
        findings: list[RawFinding] = []

        try:
            if namespace:
                reports = await self._get_namespace_reports(namespace)
            else:
                reports = await self._get_all_reports()

            for report in reports:
                findings.extend(self._extract_vulnerabilities(report))

            logger.info(
                "TrivyCollector: collected %d findings from %d VulnerabilityReports",
                len(findings),
                len(reports),
            )

        except Exception as e:
            logger.error("TrivyCollector error: %s", e, exc_info=True)

        return findings

    async def _get_namespace_reports(self, namespace: str) -> list[dict]:
        try:
            response = await self.custom_api.list_namespaced_custom_object(
                group=TRIVY_GROUP,
                version=TRIVY_VERSION,
                namespace=namespace,
                plural=VULN_REPORT_PLURAL,
            )
            return response.get("items", [])
        except Exception as e:
            logger.warning("Failed to get VulnerabilityReports in namespace %s: %s", namespace, e)
            return []

    async def _get_all_reports(self) -> list[dict]:
        try:
            response = await self.custom_api.list_cluster_custom_object(
                group=TRIVY_GROUP,
                version=TRIVY_VERSION,
                plural=VULN_REPORT_PLURAL,
            )
            return response.get("items", [])
        except Exception as e:
            logger.warning("Failed to get all VulnerabilityReports: %s", e)
            return []

    def _extract_vulnerabilities(self, report: dict) -> list[RawFinding]:
        """
        Parse VulnerabilityReport → list[RawFinding].

        Mỗi vulnerability entry trở thành 1 RawFinding với đầy đủ CVE info.
        """
        findings = []
        metadata = report.get("metadata", {})
        labels = metadata.get("labels", {})
        report_data = report.get("report", {})

        # Resource info từ labels (Trivy Operator gán labels chuẩn)
        resource_kind = labels.get("trivy-operator.resource.kind", "ReplicaSet")
        resource_name = labels.get("trivy-operator.resource.name", metadata.get("name", "unknown"))
        resource_namespace = labels.get(
            "trivy-operator.resource.namespace", metadata.get("namespace", "")
        )
        container_name = labels.get("trivy-operator.container.name", "")

        artifact = report_data.get("artifact", {})
        image_ref = f"{artifact.get('repository', 'unknown')}:{artifact.get('tag', 'unknown')}"

        for vuln in report_data.get("vulnerabilities", []):
            severity = vuln.get("severity", "UNKNOWN").lower()
            vuln_id = vuln.get("vulnerabilityID", "CVE-UNKNOWN")

            raw_finding = RawFinding(
                source="trivy",
                raw_data={
                    "vulnerability_id": vuln_id,
                    "resource_name": resource_name,
                    "resource_kind": resource_kind,
                    "resource_namespace": resource_namespace,
                    "container_name": container_name,
                    "image": image_ref,
                    "package": vuln.get("resource", ""),
                    "installed_version": vuln.get("installedVersion", ""),
                    "fixed_version": vuln.get("fixedVersion", ""),
                    "severity": severity,
                    "title": vuln.get("title", f"Vulnerability: {vuln_id}"),
                    "description": vuln.get("description", ""),
                    "primary_link": vuln.get("primaryLink", ""),
                    "score": vuln.get("score", 0.0),
                    # Summary for quick stats
                    "summary": report_data.get("summary", {}),
                },
            )
            findings.append(raw_finding)

        return findings
