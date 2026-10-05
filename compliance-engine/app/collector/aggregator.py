"""
ComplianceAggregator — Orchestrate tất cả collectors.

Thu thập song song từ 3 sources: Kyverno, Trivy, kube-bench.
Sau đó deduplicate findings có cùng resource + policy.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from itertools import chain
from typing import Optional

from kubernetes_asyncio.client import ApiClient

from app.collector.kyverno import KyvernoCollector
from app.collector.trivy import TrivyCollector
from app.collector.kubebench import KubeBenchCollector
from app.models.finding import RawFinding

logger = logging.getLogger(__name__)


class ComplianceAggregator:
    """
    Orchestrates parallel data collection from all 3 compliance sources.

    Deduplication strategy: hash(source + resource_kind + resource_name + policy/vuln_id)
    Nếu cùng hash → chỉ giữ entry đầu tiên (latest PolicyReport wins).
    """

    def __init__(self, k8s_client: ApiClient) -> None:
        self.kyverno = KyvernoCollector(k8s_client)
        self.trivy = TrivyCollector(k8s_client)
        self.kubebench = KubeBenchCollector(k8s_client)

    async def collect_all(self, namespace: Optional[str] = None) -> list[RawFinding]:
        """
        Thu thập compliance data từ tất cả sources song song.

        Args:
            namespace: Filter namespace (None = tất cả namespaces).
                       kube-bench luôn cluster-wide.

        Returns:
            list[RawFinding] đã deduplicate.
        """
        logger.info("Starting compliance collection (namespace=%s)", namespace or "all")

        # Thu thập song song — giảm latency đáng kể (3x nhanh hơn tuần tự)
        results = await asyncio.gather(
            self.kyverno.collect(namespace),
            self.trivy.collect(namespace),
            self.kubebench.collect(),  # kube-bench always cluster-wide
            return_exceptions=True,  # Không fail toàn bộ nếu 1 source lỗi
        )

        all_findings: list[RawFinding] = []

        for i, result in enumerate(results):
            source_name = ["kyverno", "trivy", "kube-bench"][i]
            if isinstance(result, Exception):
                logger.error("Collector %s failed: %s", source_name, result, exc_info=result)
                # Continue với các source khác
            else:
                logger.info("Collected %d findings from %s", len(result), source_name)
                all_findings.extend(result)

        # Deduplicate
        deduped = self._deduplicate(all_findings)
        logger.info(
            "Aggregation complete: %d raw → %d deduplicated findings",
            len(all_findings),
            len(deduped),
        )

        return deduped

    def _deduplicate(self, findings: list[RawFinding]) -> list[RawFinding]:
        """
        Loại bỏ duplicate findings dựa trên content hash.

        Kyverno có thể tạo nhiều PolicyReport cho cùng resource/policy
        (e.g., mỗi lần scan → tạo mới). Giữ entry đầu tiên.
        """
        seen_hashes: set[str] = set()
        unique: list[RawFinding] = []

        for finding in findings:
            key = self._compute_dedup_key(finding)
            if key not in seen_hashes:
                seen_hashes.add(key)
                unique.append(finding)

        return unique

    def _compute_dedup_key(self, finding: RawFinding) -> str:
        """Tính dedup key từ các trường phân biệt finding."""
        data = finding.raw_data

        # Source-specific key components
        if finding.source == "kyverno":
            key_str = f"kyverno:{data.get('policy', '')}:{data.get('resource_kind', '')}:{data.get('resource_name', '')}:{data.get('resource_namespace', '')}"
        elif finding.source == "trivy":
            key_str = f"trivy:{data.get('vulnerability_id', '')}:{data.get('resource_name', '')}:{data.get('container_name', '')}"
        else:  # kube-bench
            key_str = f"kube-bench:{data.get('test_number', '')}"

        return hashlib.md5(key_str.encode()).hexdigest()  # noqa: S324 — dedup only, not security

    async def health_check(self) -> dict[str, bool]:
        """Kiểm tra health của tất cả collectors."""
        results = await asyncio.gather(
            self.kyverno.health_check(),
            self.trivy.health_check(),
            self.kubebench.health_check(),
            return_exceptions=True,
        )

        return {
            "kyverno": results[0] if not isinstance(results[0], Exception) else False,
            "trivy": results[1] if not isinstance(results[1], Exception) else False,
            "kube-bench": results[2] if not isinstance(results[2], Exception) else False,
        }
