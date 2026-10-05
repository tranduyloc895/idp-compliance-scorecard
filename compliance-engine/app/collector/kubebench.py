"""
KubeBenchCollector — Đọc kube-bench JSON từ ConfigMap.

kube-bench CronJob chạy mỗi giờ, lưu kết quả JSON vào ConfigMap
`kube-bench-results` trong namespace `monitoring`.

Flow:
  CronJob → kubectl apply → ConfigMap `kube-bench-results` → Collector đọc
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from kubernetes_asyncio.client import ApiClient, CoreV1Api

from app.collector.base import BaseCollector
from app.models.finding import RawFinding

logger = logging.getLogger(__name__)

# ConfigMap chứa kết quả kube-bench
KUBEBENCH_CONFIGMAP_NAME = "kube-bench-results"
KUBEBENCH_CONFIGMAP_NAMESPACE = "monitoring"
KUBEBENCH_CONFIGMAP_KEY = "results.json"

# CIS section → compliance category mapping
CIS_SECTION_TO_CATEGORY = {
    "1": "cluster_security",  # Control Plane Components
    "2": "cluster_security",  # etcd
    "3": "cluster_security",  # Control Plane Configuration
    "4": "workload_security",  # Worker Node Security Configuration
    "5": "platform_config",  # Kubernetes Policies
}

# Severity mapping cho CIS tests
CIS_STATUS_TO_SEVERITY = {
    "FAIL": "high",  # CIS FAIL → HIGH severity by default
    "WARN": "medium",
    "INFO": "info",
    "PASS": "info",
}


class KubeBenchCollector(BaseCollector):
    """
    Collector cho kube-bench CIS Kubernetes Benchmark results.

    Đọc JSON từ ConfigMap, parse per-section results,
    map mỗi CIS test → RawFinding.
    """

    def __init__(self, k8s_client: ApiClient) -> None:
        super().__init__(k8s_client)
        self.core_api = CoreV1Api(k8s_client)

    async def collect(self, namespace: Optional[str] = None) -> list[RawFinding]:
        """
        Collect kube-bench results.

        Note: kube-bench là cluster-level check, namespace param được bỏ qua.
        Resource sẽ là cluster node, không phải workload namespace.

        Returns:
            list[RawFinding] với source="kube-bench"
        """
        findings: list[RawFinding] = []

        try:
            raw_json = await self._get_results_from_configmap()
            if not raw_json:
                logger.warning("kube-bench ConfigMap not found or empty, skipping")
                return []

            results_data = json.loads(raw_json)
            findings = self._parse_results(results_data)

            logger.info(
                "KubeBenchCollector: collected %d findings from ConfigMap",
                len(findings),
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse kube-bench JSON: %s", e)
        except Exception as e:
            logger.error("KubeBenchCollector error: %s", e, exc_info=True)

        return findings

    async def _get_results_from_configmap(self) -> Optional[str]:
        """Đọc kết quả kube-bench từ ConfigMap."""
        try:
            configmap = await self.core_api.read_namespaced_config_map(
                name=KUBEBENCH_CONFIGMAP_NAME,
                namespace=KUBEBENCH_CONFIGMAP_NAMESPACE,
            )
            return configmap.data.get(KUBEBENCH_CONFIGMAP_KEY) if configmap.data else None
        except Exception as e:
            logger.warning(
                "ConfigMap %s/%s not found: %s",
                KUBEBENCH_CONFIGMAP_NAMESPACE,
                KUBEBENCH_CONFIGMAP_NAME,
                e,
            )
            return None

    def _parse_results(self, data: dict) -> list[RawFinding]:
        """
        Parse kube-bench JSON output → list[RawFinding].

        kube-bench JSON structure:
        {
          "Controls": [
            {
              "id": "1",
              "text": "Control Plane Components",
              "tests": [
                {
                  "section": "1.1",
                  "results": [
                    {
                      "test_number": "1.1.1",
                      "test_desc": "...",
                      "status": "PASS|FAIL|WARN|INFO",
                      ...
                    }
                  ]
                }
              ]
            }
          ]
        }
        """
        findings = []

        # Handle both single result and list of results (kube-bench can output multiple nodes)
        controls_list = data.get("Controls", [])
        if not controls_list and isinstance(data, list):
            # Multiple node results — flatten
            for node_data in data:
                controls_list.extend(node_data.get("Controls", []))

        for control_group in controls_list:
            group_id = str(control_group.get("id", "0"))
            category = CIS_SECTION_TO_CATEGORY.get(group_id, "platform_config")

            for test_section in control_group.get("tests", []):
                for result in test_section.get("results", []):
                    test_number = result.get("test_number", "0.0.0")
                    status = result.get("status", "WARN")
                    test_desc = result.get("test_desc", "Unknown test")
                    remediation = result.get("remediation", "")
                    actual_value = result.get("actual_value", "")

                    # CRITICAL cho các control cụ thể về API server anonymous auth
                    severity = self._determine_severity(test_number, status)

                    raw_finding = RawFinding(
                        source="kube-bench",
                        raw_data={
                            "test_number": test_number,
                            "test_desc": test_desc,
                            "status": status,  # "PASS" | "FAIL" | "WARN" | "INFO"
                            "severity": severity,
                            "category": category,
                            "remediation": remediation,
                            "actual_value": actual_value,
                            "scored": result.get("scored", True),
                            "expected_result": result.get("expected_result", ""),
                            # Resource = cluster node (không có namespace)
                            "resource_kind": "Node",
                            "resource_name": "cluster",
                            "resource_namespace": None,
                        },
                    )
                    findings.append(raw_finding)

        return findings

    def _determine_severity(self, test_number: str, status: str) -> str:
        """
        Xác định severity cho CIS test.

        Một số test_number đặc biệt có severity CRITICAL (API server config).
        """
        if status in ("PASS", "INFO"):
            return "info"

        # Critical CIS controls
        critical_tests = {
            "1.2.1",  # API server anonymous auth
            "1.2.6",  # kubelet certificate authority
            "4.2.1",  # kubelet anonymous auth
            "1.3.2",  # controller manager profiling
            "2.1",  # etcd cert file
            "2.2",  # etcd key file
        }

        if test_number in critical_tests and status == "FAIL":
            return "critical"

        return CIS_STATUS_TO_SEVERITY.get(status, "medium")
