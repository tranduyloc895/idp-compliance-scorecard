"""
Scoring weights và penalty configuration.

Tách ra file riêng để dễ điều chỉnh không cần sửa logic engine.
Thay đổi weights ảnh hưởng trực tiếp đến overall score calculation.
"""

from app.models.finding import ComplianceCategory, Severity

# ---------------------------------------------------------------------------
# Domain weights — phải sum = 1.0
# ---------------------------------------------------------------------------
DOMAIN_WEIGHTS: dict[ComplianceCategory, float] = {
    ComplianceCategory.CLUSTER_SECURITY: 0.35,   # CIS control plane / etcd / network
    ComplianceCategory.WORKLOAD_SECURITY: 0.35,  # Pod security / RBAC
    ComplianceCategory.SUPPLY_CHAIN: 0.20,        # Image CVEs / tag policy
    ComplianceCategory.PLATFORM_CONFIG: 0.10,    # Labels / limits / probes
}

# Validation: đảm bảo weights sum = 1.0
_weight_sum = sum(DOMAIN_WEIGHTS.values())
assert abs(_weight_sum - 1.0) < 1e-9, f"Domain weights must sum to 1.0, got {_weight_sum}"

# ---------------------------------------------------------------------------
# Severity penalties — điểm trừ cho mỗi FAIL finding theo severity
# ---------------------------------------------------------------------------
# NOTE: Penalties áp dụng PER FINDING (không phải per category)
# Cap: score không xuống dưới 0
SEVERITY_PENALTIES: dict[Severity, float] = {
    Severity.CRITICAL: 15.0,  # -15 per CRITICAL FAIL
    Severity.HIGH: 5.0,       # -5 per HIGH FAIL
    Severity.MEDIUM: 0.0,     # Không penalty (tính qua pass rate)
    Severity.LOW: 0.0,
    Severity.INFO: 0.0,
}

# Maximum penalty cap cho 1 domain (để tránh 1 domain kéo overall về 0)
MAX_DOMAIN_PENALTY: float = 50.0
