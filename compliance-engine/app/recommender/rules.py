"""
Rule-based recommender — 25 cứng hóa rules cho common Kubernetes violations.

Ưu điểm: Deterministic, <1ms latency, template YAML chính xác.
Nhược điểm: Coverage giới hạn, không xử lý được unseen violations.

Dùng cho so sánh nghiên cứu:
  Rule-based vs AI (Basic prompt) vs AI (Context-enriched prompt)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.models.finding import UnifiedComplianceFinding
from app.models.recommendation import RuleRecommendation

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class Rule:
    """Định nghĩa 1 rule-based recommendation."""

    rule_id: str
    title: str
    fix_description: str
    yaml_template: str  # Filename trong templates/ directory
    reference: str  # CIS Benchmark / NIST / NSA reference
    # Keywords để match với finding.finding_id hoặc finding.title
    keywords: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 25 Rules — covering tất cả 8 Kyverno policies + common CVE patterns
# ---------------------------------------------------------------------------
RULES: dict[str, Rule] = {
    # Workload Security
    "require-run-as-non-root": Rule(
        rule_id="WS-001",
        title="Container runs as root (UID 0)",
        fix_description=(
            "Add securityContext.runAsNonRoot: true and runAsUser: 1000 "
            "to prevent container processes from running with root privileges."
        ),
        yaml_template="run-as-non-root.yaml",
        reference="CIS Kubernetes Benchmark 5.2.6 | NSA Kubernetes Hardening Guide p.21",
        keywords=["require-run-as-non-root", "run-as-non-root", "runs as root", "runasnonroot"],
    ),
    "disallow-privilege-escalation": Rule(
        rule_id="WS-002",
        title="Container allows privilege escalation",
        fix_description=(
            "Set securityContext.allowPrivilegeEscalation: false to prevent "
            "container processes from gaining additional privileges."
        ),
        yaml_template="disallow-privilege-escalation.yaml",
        reference="CIS Kubernetes Benchmark 5.2.5 | NIST SP 800-190 Section 4.2",
        keywords=["disallow-privilege-escalation", "privilege-escalation", "allowprivilegeescalation"],
    ),
    "require-read-only-rootfs": Rule(
        rule_id="WS-003",
        title="Container has writable root filesystem",
        fix_description=(
            "Set securityContext.readOnlyRootFilesystem: true. "
            "If the app needs write access, mount specific directories as emptyDir volumes."
        ),
        yaml_template="read-only-rootfs.yaml",
        reference="CIS Kubernetes Benchmark 5.2.4 | NSA Kubernetes Hardening Guide p.23",
        keywords=["require-read-only-rootfs", "read-only-rootfs", "readonlyrootfilesystem"],
    ),
    "drop-all-capabilities": Rule(
        rule_id="WS-004",
        title="Container does not drop all Linux capabilities",
        fix_description=(
            "Add securityContext.capabilities.drop: [ALL] to remove all Linux capabilities. "
            "If specific capabilities are needed, add them explicitly via capabilities.add."
        ),
        yaml_template="drop-capabilities.yaml",
        reference="CIS Kubernetes Benchmark 5.2.7 | NSA Kubernetes Hardening Guide p.24",
        keywords=["drop-all-capabilities", "drop-capabilities", "capabilities"],
    ),
    # Supply Chain
    "disallow-latest-tag": Rule(
        rule_id="SC-001",
        title="Container uses image with :latest tag",
        fix_description=(
            "Replace ':latest' with a specific version tag (e.g., ':1.24.0') or "
            "better yet, a SHA256 digest (e.g., '@sha256:...'). "
            "This ensures reproducible deployments."
        ),
        yaml_template="disallow-latest-tag.yaml",
        reference="CIS Kubernetes Benchmark 5.4.1 | NIST SP 800-190 Section 4.1",
        keywords=["disallow-latest-tag", "latest-tag", "latest tag", "image tag"],
    ),
    # Platform Config
    "require-resource-limits": Rule(
        rule_id="PC-001",
        title="Container has no resource limits (CPU/Memory)",
        fix_description=(
            "Add resources.limits.cpu and resources.limits.memory to every container. "
            "Without limits, a single pod can consume all node resources."
        ),
        yaml_template="resource-limits.yaml",
        reference="CIS Kubernetes Benchmark 5.2.11 | Kubernetes Best Practices",
        keywords=["require-resource-limits", "resource-limits", "resource limits", "no limits"],
    ),
    "require-labels": Rule(
        rule_id="PC-002",
        title="Resource missing required labels",
        fix_description=(
            "Add required labels: app.kubernetes.io/name and app.kubernetes.io/version. "
            "These labels enable proper service discovery, monitoring, and GitOps workflows."
        ),
        yaml_template="require-labels.yaml",
        reference="Kubernetes Recommended Labels | Platform Config Standard",
        keywords=["require-labels", "missing labels", "app.kubernetes.io"],
    ),
    "require-probes": Rule(
        rule_id="PC-003",
        title="Container missing liveness or readiness probes",
        fix_description=(
            "Add livenessProbe and readinessProbe to the container spec. "
            "Probes enable Kubernetes to detect and recover from application failures automatically."
        ),
        yaml_template="require-probes.yaml",
        reference="Kubernetes Probe Best Practices | Platform Config Standard",
        keywords=["require-probes", "missing probes", "liveness", "readiness"],
    ),
    # CVE severity patterns (Trivy)
    "trivy-critical-cve": Rule(
        rule_id="SC-002",
        title="Critical CVE detected in container image",
        fix_description=(
            "Update the affected package to a fixed version immediately. "
            "Run 'trivy image <image>:<tag>' to see the specific fix version. "
            "Update your Dockerfile to upgrade the vulnerable package."
        ),
        yaml_template="disallow-latest-tag.yaml",  # Pin image to fixed version
        reference="NIST NVD CVE Database | CIS Kubernetes Benchmark 5.4.1",
        keywords=["cve-202", "critical cve", "vulnerability", "trv-cve"],
    ),
    "trivy-high-cve": Rule(
        rule_id="SC-003",
        title="High severity CVE detected in container image",
        fix_description=(
            "Update the affected package to the fixed version in your next deployment. "
            "Review CVE details for exploitability context. "
            "Consider using distroless base images to reduce attack surface."
        ),
        yaml_template="disallow-latest-tag.yaml",
        reference="NIST NVD CVE Database | Docker Security Best Practices",
        keywords=["high cve", "high severity", "high vulnerability"],
    ),
    # CIS kube-bench patterns
    "cis-1.2.1": Rule(
        rule_id="CS-001",
        title="API server allows anonymous authentication",
        fix_description=(
            "Add --anonymous-auth=false to the kube-apiserver arguments in "
            "/etc/kubernetes/manifests/kube-apiserver.yaml. "
            "This prevents unauthenticated access to the API server."
        ),
        yaml_template="security-context-full.yaml",
        reference="CIS Kubernetes Benchmark 1.2.1 | NSA Kubernetes Hardening Guide p.6",
        keywords=["cis-1.2.1", "anonymous-auth", "anonymous auth", "anonymous authentication"],
    ),
    "cis-4.2.1": Rule(
        rule_id="CS-002",
        title="Kubelet allows anonymous authentication",
        fix_description=(
            "Set authentication.anonymous.enabled: false in kubelet config file "
            "or add --anonymous-auth=false to kubelet arguments."
        ),
        yaml_template="security-context-full.yaml",
        reference="CIS Kubernetes Benchmark 4.2.1 | NSA Kubernetes Hardening Guide p.8",
        keywords=["cis-4.2.1", "kubelet anonymous", "kubelet authentication"],
    ),
    "cis-5.1.6": Rule(
        rule_id="CS-003",
        title="Service account token auto-mounted",
        fix_description=(
            "Set automountServiceAccountToken: false in the ServiceAccount spec "
            "and explicitly opt-in pods that need it."
        ),
        yaml_template="security-context-full.yaml",
        reference="CIS Kubernetes Benchmark 5.1.6 | RBAC Best Practices",
        keywords=["cis-5.1.6", "automountserviceaccounttoken", "service account token"],
    ),
    # Network
    "require-network-policy": Rule(
        rule_id="CS-004",
        title="Namespace lacks Network Policy (all traffic allowed)",
        fix_description=(
            "Create a default-deny NetworkPolicy, then add allow rules for "
            "required communication paths only."
        ),
        yaml_template="network-policy.yaml",
        reference="CIS Kubernetes Benchmark 5.3.2 | NSA Kubernetes Hardening Guide p.12",
        keywords=["network-policy", "networkpolicy", "no network policy", "traffic allowed"],
    ),
    # Security Context comprehensive
    "missing-security-context": Rule(
        rule_id="WS-005",
        title="Container missing security context",
        fix_description=(
            "Add a comprehensive securityContext to the container with: "
            "runAsNonRoot, readOnlyRootFilesystem, allowPrivilegeEscalation: false, "
            "and capabilities.drop: [ALL]."
        ),
        yaml_template="security-context-full.yaml",
        reference="CIS Kubernetes Benchmark 5.2 | NSA Kubernetes Hardening Guide",
        keywords=["security-context", "securitycontext", "missing security"],
    ),
}


class RuleBasedRecommender:
    """
    Sinh recommendation từ predefined rules.

    Matching strategy:
    1. Exact match: finding_id exact match với rule key
    2. Keyword match: finding_id hoặc title chứa rule keyword
    3. None: finding không có rule → return None
    """

    def get_recommendation(
        self,
        finding: UnifiedComplianceFinding,
    ) -> Optional[RuleRecommendation]:
        """
        Lấy rule-based recommendation cho finding.

        Returns:
            RuleRecommendation nếu có rule phù hợp, None nếu không.
        """
        rule = self._find_matching_rule(finding)
        if not rule:
            logger.debug(
                "No rule-based recommendation for finding: %s", finding.finding_id
            )
            return None

        # Load YAML template
        yaml_fix = self._load_template(rule.yaml_template)

        return RuleRecommendation(
            finding_id=finding.finding_id,
            rule_id=rule.rule_id,
            title=rule.title,
            fix_description=rule.fix_description,
            yaml_fix=yaml_fix,
            reference=rule.reference,
        )

    def _find_matching_rule(
        self,
        finding: UnifiedComplianceFinding,
    ) -> Optional[Rule]:
        """
        Tìm rule phù hợp nhất cho finding.

        Priority: exact finding_id match > keyword match
        """
        finding_id_lower = finding.finding_id.lower()
        title_lower = finding.title.lower()
        description_lower = finding.description.lower()

        # 1. Try exact key match (policy name in finding_id)
        for rule_key, rule in RULES.items():
            if rule_key in finding_id_lower:
                return rule

        # 2. Try keyword match
        for rule in RULES.values():
            for keyword in rule.keywords:
                if keyword in finding_id_lower or keyword in title_lower or keyword in description_lower:
                    return rule

        return None

    def _load_template(self, template_filename: str) -> str:
        """Load YAML fix template từ templates/ directory."""
        template_path = TEMPLATES_DIR / template_filename
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Template not found: %s", template_path)
            return f"# Template '{template_filename}' not found\n# Please check the templates/ directory"

    def get_coverage_stats(self) -> dict:
        """Thống kê coverage cho thực nghiệm."""
        return {
            "total_rules": len(RULES),
            "categories": {
                "workload_security": sum(1 for r in RULES.values() if r.rule_id.startswith("WS")),
                "supply_chain": sum(1 for r in RULES.values() if r.rule_id.startswith("SC")),
                "platform_config": sum(1 for r in RULES.values() if r.rule_id.startswith("PC")),
                "cluster_security": sum(1 for r in RULES.values() if r.rule_id.startswith("CS")),
            },
        }
