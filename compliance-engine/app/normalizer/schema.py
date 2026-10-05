"""
Normalizer Schema — Transform functions và lookup tables.

Mỗi source (Kyverno, Trivy, kube-bench) có raw data format khác nhau.
Module này định nghĩa:
  - Lookup tables: policy_name → category, severity
  - Transform functions: raw_data dict → typed values
"""

from __future__ import annotations

from app.models.finding import ComplianceCategory, Severity, FindingStatus

# ---------------------------------------------------------------------------
# Kyverno Policy → Category + Severity lookup table
# ---------------------------------------------------------------------------
# Policy name (từ ClusterPolicy metadata.name) → (category, severity)
KYVERNO_POLICY_MAP: dict[str, tuple[ComplianceCategory, Severity]] = {
    # Workload Security policies
    "disallow-privilege-escalation": (ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH),
    "require-run-as-non-root": (ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH),
    "require-read-only-rootfs": (ComplianceCategory.WORKLOAD_SECURITY, Severity.MEDIUM),
    "drop-all-capabilities": (ComplianceCategory.WORKLOAD_SECURITY, Severity.HIGH),
    # Supply Chain policies
    "disallow-latest-tag": (ComplianceCategory.SUPPLY_CHAIN, Severity.HIGH),
    # Platform Config policies
    "require-resource-limits": (ComplianceCategory.PLATFORM_CONFIG, Severity.MEDIUM),
    "require-labels": (ComplianceCategory.PLATFORM_CONFIG, Severity.LOW),
    "require-probes": (ComplianceCategory.PLATFORM_CONFIG, Severity.MEDIUM),
}

# Fallback khi policy không có trong lookup table
KYVERNO_DEFAULT_CATEGORY = ComplianceCategory.WORKLOAD_SECURITY
KYVERNO_DEFAULT_SEVERITY = Severity.MEDIUM

# ---------------------------------------------------------------------------
# Trivy severity string → Severity enum
# ---------------------------------------------------------------------------
TRIVY_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "unknown": Severity.INFO,
}

# ---------------------------------------------------------------------------
# kube-bench status → FindingStatus
# ---------------------------------------------------------------------------
KUBEBENCH_STATUS_MAP: dict[str, FindingStatus] = {
    "PASS": FindingStatus.PASS,
    "FAIL": FindingStatus.FAIL,
    "WARN": FindingStatus.WARN,
    "INFO": FindingStatus.PASS,  # INFO = passing, not actionable
}

# kube-bench category mapping (xác định từ test number prefix)
# Section → ComplianceCategory
KUBEBENCH_SECTION_MAP: dict[str, ComplianceCategory] = {
    "1": ComplianceCategory.CLUSTER_SECURITY,  # Control Plane
    "2": ComplianceCategory.CLUSTER_SECURITY,  # etcd
    "3": ComplianceCategory.CLUSTER_SECURITY,  # Control Plane Config
    "4": ComplianceCategory.WORKLOAD_SECURITY,  # Worker Node Security
    "5": ComplianceCategory.PLATFORM_CONFIG,  # Kubernetes Policies
}


def get_kyverno_category_severity(
    policy_name: str,
) -> tuple[ComplianceCategory, Severity]:
    """Lookup category và severity cho Kyverno policy."""
    # Normalize: lowercase + strip whitespace
    normalized = policy_name.lower().strip()
    if normalized in KYVERNO_POLICY_MAP:
        return KYVERNO_POLICY_MAP[normalized]
    # Partial match (e.g., "cpol-require-run-as-non-root" → "require-run-as-non-root")
    for key, value in KYVERNO_POLICY_MAP.items():
        if key in normalized:
            return value
    return KYVERNO_DEFAULT_CATEGORY, KYVERNO_DEFAULT_SEVERITY


def get_trivy_severity(severity_str: str) -> Severity:
    """Convert Trivy severity string → Severity enum."""
    return TRIVY_SEVERITY_MAP.get(severity_str.lower(), Severity.INFO)


def get_kubebench_category(test_number: str) -> ComplianceCategory:
    """Xác định ComplianceCategory từ CIS test number prefix."""
    if not test_number:
        return ComplianceCategory.CLUSTER_SECURITY
    section = test_number.split(".")[0]
    return KUBEBENCH_SECTION_MAP.get(section, ComplianceCategory.PLATFORM_CONFIG)


def get_kubebench_status(status_str: str) -> FindingStatus:
    """Convert kube-bench status string → FindingStatus enum."""
    return KUBEBENCH_STATUS_MAP.get(status_str.upper(), FindingStatus.WARN)


def normalize_severity_from_str(severity_str: str) -> Severity:
    """Generic severity normalizer từ bất kỳ string nào."""
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
        "informational": Severity.INFO,
        "warn": Severity.MEDIUM,
        "warning": Severity.MEDIUM,
    }
    return mapping.get(severity_str.lower(), Severity.INFO)


def normalize_status_from_kyverno(result_str: str) -> FindingStatus:
    """Convert Kyverno result string → FindingStatus."""
    mapping = {
        "pass": FindingStatus.PASS,
        "fail": FindingStatus.FAIL,
        "warn": FindingStatus.WARN,
        "error": FindingStatus.FAIL,
        "skip": FindingStatus.SKIP,
    }
    return mapping.get(result_str.lower(), FindingStatus.WARN)
