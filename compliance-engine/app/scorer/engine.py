"""
ComplianceScorer — Weighted scoring engine.

Algorithm:
  1. Group findings by ComplianceCategory
  2. Per domain:
     a. base_score = (passed / total) * 100
     b. penalty = Σ(penalty[severity] for each FAIL finding with CRITICAL/HIGH)
     c. domain_score = clamp(base_score - penalty, 0, 100)
  3. overall_score = Σ(weight_i × domain_score_i)
  4. Classify → Excellent/Good/Fair/Poor

Note: Domains với 0 findings nhận score = 100.0 (no violations = pass).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from app.models.finding import (
    ComplianceCategory,
    FindingStatus,
    Severity,
    UnifiedComplianceFinding,
)
from app.models.score import DomainScore, ScoreResult
from app.scorer.classifier import classify_score
from app.scorer.weights import DOMAIN_WEIGHTS, MAX_DOMAIN_PENALTY, SEVERITY_PENALTIES

logger = logging.getLogger(__name__)


class ComplianceScorer:
    """
    Tính compliance score từ list of UnifiedComplianceFinding.

    Stateless — mỗi lần gọi calculate() tạo ScoreResult mới.
    """

    def calculate(
        self,
        findings: list[UnifiedComplianceFinding],
        scan_id: int,
        namespace: Optional[str] = None,
    ) -> ScoreResult:
        """
        Tính toán compliance score.

        Args:
            findings: Tất cả unified findings từ normalizer.
            scan_id: ID của scan hiện tại.
            namespace: Namespace filter (None = cluster-wide).

        Returns:
            ScoreResult với overall score và domain breakdown.
        """
        logger.info(
            "Calculating compliance score: %d findings, namespace=%s",
            len(findings),
            namespace or "all",
        )

        # 1. Group findings by category
        by_category: dict[ComplianceCategory, list[UnifiedComplianceFinding]] = defaultdict(list)
        for finding in findings:
            by_category[finding.category].append(finding)

        # 2. Calculate per-domain scores
        domain_scores: list[DomainScore] = []
        for category, weight in DOMAIN_WEIGHTS.items():
            domain_findings = by_category.get(category, [])
            domain_score = self._calculate_domain_score(category, weight, domain_findings)
            domain_scores.append(domain_score)

        # 3. Weighted overall score
        overall_score = sum(d.score * d.weight for d in domain_scores)
        overall_score = round(min(max(overall_score, 0.0), 100.0), 2)

        # 4. Classify
        classification = classify_score(overall_score)

        # 5. Summary counters
        total_findings = len(findings)
        total_passed = sum(1 for f in findings if f.status == FindingStatus.PASS)
        total_failed = sum(1 for f in findings if f.status == FindingStatus.FAIL)
        critical_violations = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.CRITICAL
        )
        high_violations = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.HIGH
        )

        result = ScoreResult(
            scan_id=scan_id,
            overall_score=overall_score,
            classification=classification,
            domains=domain_scores,
            scanned_at=datetime.utcnow(),
            namespace=namespace,
            total_findings=total_findings,
            total_passed=total_passed,
            total_failed=total_failed,
            critical_violations=critical_violations,
            high_violations=high_violations,
        )

        logger.info(
            "Score calculated: %.1f (%s) | %d total, %d pass, %d fail, %d critical",
            overall_score,
            classification.value,
            total_findings,
            total_passed,
            total_failed,
            critical_violations,
        )

        return result

    def _calculate_domain_score(
        self,
        category: ComplianceCategory,
        weight: float,
        findings: list[UnifiedComplianceFinding],
    ) -> DomainScore:
        """
        Tính score cho 1 compliance domain.

        Công thức:
          base = (passed / total) * 100    [nếu total = 0 → base = 100]
          penalty = Σ penalty[sev] for each FAIL with CRITICAL/HIGH
          score = clamp(base - penalty, 0, 100)
        """
        if not findings:
            # No findings → perfect score (no violations detected)
            return DomainScore(
                domain=category,
                score=100.0,
                weight=weight,
                total_checks=0,
                passed=0,
                failed=0,
                warned=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
            )

        total = len(findings)
        passed = sum(1 for f in findings if f.status == FindingStatus.PASS)
        failed = sum(1 for f in findings if f.status == FindingStatus.FAIL)
        warned = sum(1 for f in findings if f.status == FindingStatus.WARN)

        # Severity breakdown (failed only)
        critical_count = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.CRITICAL
        )
        high_count = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.HIGH
        )
        medium_count = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.MEDIUM
        )
        low_count = sum(
            1 for f in findings
            if f.status == FindingStatus.FAIL and f.severity == Severity.LOW
        )

        # Base score từ pass rate
        base_score = (passed / total) * 100.0

        # Severity penalty (chỉ CRITICAL và HIGH)
        penalty = (
            critical_count * SEVERITY_PENALTIES[Severity.CRITICAL]
            + high_count * SEVERITY_PENALTIES[Severity.HIGH]
        )
        # Cap penalty để không kéo domain về 0 quá dễ
        penalty = min(penalty, MAX_DOMAIN_PENALTY)

        domain_score = max(0.0, min(100.0, base_score - penalty))
        domain_score = round(domain_score, 2)

        return DomainScore(
            domain=category,
            score=domain_score,
            weight=weight,
            total_checks=total,
            passed=passed,
            failed=failed,
            warned=warned,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )
