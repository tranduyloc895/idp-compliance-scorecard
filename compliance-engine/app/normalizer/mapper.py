"""
NormalizerMapper — Transform RawFinding → UnifiedComplianceFinding.

Xử lý tất cả 3 sources với logic mapping riêng cho từng source.
Output là UnifiedComplianceFinding chuẩn hóa để scorer và recommender dùng.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    K8sResource,
    RawFinding,
    Severity,
    UnifiedComplianceFinding,
)
from app.normalizer.schema import (
    get_kubebench_category,
    get_kubebench_status,
    get_kyverno_category_severity,
    get_trivy_severity,
    normalize_severity_from_str,
    normalize_status_from_kyverno,
)

logger = logging.getLogger(__name__)


class NormalizerMapper:
    """
    Maps RawFinding from any source → UnifiedComplianceFinding.

    Dispatch dựa trên raw_finding.source.
    """

    def normalize_all(self, raw_findings: list[RawFinding]) -> list[UnifiedComplianceFinding]:
        """
        Normalize tất cả raw findings.

        Findings không normalize được sẽ bị skip với log warning.
        """
        unified: list[UnifiedComplianceFinding] = []

        for raw in raw_findings:
            try:
                result = self.normalize(raw)
                if result:
                    unified.append(result)
            except Exception as e:
                logger.warning(
                    "Failed to normalize finding (source=%s): %s | data=%s",
                    raw.source,
                    e,
                    raw.raw_data,
                )

        logger.info(
            "Normalized %d/%d findings successfully",
            len(unified),
            len(raw_findings),
        )
        return unified

    def normalize(self, raw: RawFinding) -> Optional[UnifiedComplianceFinding]:
        """Dispatch normalize theo source."""
        if raw.source == "kyverno":
            return self._normalize_kyverno(raw)
        elif raw.source == "trivy":
            return self._normalize_trivy(raw)
        elif raw.source == "kube-bench":
            return self._normalize_kubebench(raw)
        else:
            logger.warning("Unknown source: %s", raw.source)
            return None

    # -----------------------------------------------------------------------
    # Kyverno
    # -----------------------------------------------------------------------

    def _normalize_kyverno(self, raw: RawFinding) -> UnifiedComplianceFinding:
        data = raw.raw_data

        policy_name = data.get("policy", "unknown")
        category, default_severity = get_kyverno_category_severity(policy_name)

        # Severity: dùng severity từ PolicyReport nếu có (override lookup table)
        severity_str = data.get("severity", "")
        severity = normalize_severity_from_str(severity_str) if severity_str else default_severity

        status = normalize_status_from_kyverno(data.get("result", "fail"))

        resource_kind = data.get("resource_kind", "Unknown")
        resource_name = data.get("resource_name", "unknown")
        resource_namespace = data.get("resource_namespace")

        # finding_id format: KYV-{policy}-{namespace}-{resource_name}
        finding_id = self._make_finding_id(
            "KYV", policy_name, resource_namespace, resource_name
        )

        return UnifiedComplianceFinding(
            finding_id=finding_id,
            source="kyverno",
            category=category,
            severity=severity,
            status=status,
            resource=K8sResource(
                kind=resource_kind,
                name=resource_name,
                namespace=resource_namespace,
            ),
            title=f"Policy violation: {policy_name}",
            description=data.get("message", f"Resource violates policy: {policy_name}"),
            collected_at=datetime.utcnow(),
            raw_metadata=data,
        )

    # -----------------------------------------------------------------------
    # Trivy
    # -----------------------------------------------------------------------

    def _normalize_trivy(self, raw: RawFinding) -> UnifiedComplianceFinding:
        data = raw.raw_data

        vuln_id = data.get("vulnerability_id", "CVE-UNKNOWN")
        severity = get_trivy_severity(data.get("severity", "unknown"))
        resource_name = data.get("resource_name", "unknown")
        resource_namespace = data.get("resource_namespace")

        # All Trivy findings → SUPPLY_CHAIN category
        category = ComplianceCategory.SUPPLY_CHAIN

        # Vulnerabilities: status = FAIL (nó tồn tại → violation)
        status = FindingStatus.FAIL

        package = data.get("package", "")
        installed = data.get("installed_version", "")
        fixed = data.get("fixed_version", "")
        image = data.get("image", "")

        description = (
            f"{data.get('description', '')} "
            f"[Package: {package} {installed}→fix: {fixed or 'no fix available'}] "
            f"[Image: {image}]"
        ).strip()

        finding_id = self._make_finding_id(
            "TRV", vuln_id, resource_namespace, resource_name
        )

        return UnifiedComplianceFinding(
            finding_id=finding_id,
            source="trivy",
            category=category,
            severity=severity,
            status=status,
            resource=K8sResource(
                kind=data.get("resource_kind", "Deployment"),
                name=resource_name,
                namespace=resource_namespace,
            ),
            title=data.get("title", f"Vulnerability: {vuln_id}"),
            description=description,
            collected_at=datetime.utcnow(),
            raw_metadata=data,
        )

    # -----------------------------------------------------------------------
    # kube-bench
    # -----------------------------------------------------------------------

    def _normalize_kubebench(self, raw: RawFinding) -> UnifiedComplianceFinding:
        data = raw.raw_data

        test_number = data.get("test_number", "0.0.0")
        test_desc = data.get("test_desc", "Unknown CIS test")
        status_str = data.get("status", "WARN")

        category = get_kubebench_category(test_number)
        status = get_kubebench_status(status_str)

        # Severity từ raw_data (đã tính trong collector)
        severity = normalize_severity_from_str(data.get("severity", "medium"))

        finding_id = f"CIS-{test_number}"

        remediation = data.get("remediation", "")
        description = test_desc
        if remediation:
            description = f"{test_desc}. Remediation: {remediation}"

        return UnifiedComplianceFinding(
            finding_id=finding_id,
            source="kube-bench",
            category=category,
            severity=severity,
            status=status,
            resource=K8sResource(
                kind="Node",
                name="cluster",
                namespace=None,  # Cluster-scoped
            ),
            title=f"CIS {test_number}: {test_desc}",
            description=description,
            collected_at=datetime.utcnow(),
            raw_metadata=data,
        )

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_finding_id(prefix: str, policy: str, namespace: Optional[str], resource: str) -> str:
        """
        Tạo finding_id ngắn gọn và unique.

        Format: {PREFIX}-{hash[:8]}
        Full key được hash để tránh ID quá dài.
        """
        full_key = f"{prefix}:{policy}:{namespace or 'cluster'}:{resource}"
        short_hash = hashlib.sha256(full_key.encode()).hexdigest()[:8]
        # Sanitize policy name (chỉ giữ chữ cái và dấu gạch ngang)
        policy_short = policy.replace("/", "-").replace("_", "-")[:30]
        return f"{prefix}-{policy_short}-{short_hash}"
