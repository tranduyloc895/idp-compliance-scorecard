"""
AI Recommender — Gemini 2.5 Flash với structured output (JSON mode).

Dùng google-genai SDK (v1.0+) với native JSON response mode.
Hỗ trợ 2 prompt strategies cho thực nghiệm so sánh.

Latency đo và lưu vào RecommendationRecord.latency_ms cho thesis experiment.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.models.finding import UnifiedComplianceFinding
from app.models.recommendation import AIRecommendation
from app.models.ai_summary import AISummary, RemediationPlan
from app.recommender.prompts import (
    build_basic_prompt,
    build_context_enriched_prompt,
    build_executive_summary_prompt,
    build_remediation_plan_prompt,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output schema (JSON mode) — Gemini native response schema
# ---------------------------------------------------------------------------

class AIRecommendationSchema(BaseModel):
    """
    Schema cho Gemini structured output.

    Gemini 2.5 Flash sẽ generate JSON theo schema này.
    Sau đó validate bằng Pydantic (double validation).
    """

    root_cause: str = Field(
        ...,
        description="Root cause of the violation and its security impact",
    )
    yaml_fix: str = Field(
        ...,
        description="Drop-in YAML snippet that resolves the violation. Must be valid YAML.",
    )
    impact_if_unfixed: str = Field(
        ...,
        description="Security impact and risk if this violation is not fixed",
    )
    cis_references: list[str] = Field(
        default_factory=list,
        description='List of CIS Benchmark control numbers, e.g. ["5.2.6", "5.2.7"]',
    )
    urgency: Literal["immediate", "soon", "low"] = Field(
        default="soon",
        description="Fix urgency: immediate (CRITICAL, actively exploitable), soon (HIGH, exploit likely), low (MEDIUM/LOW)",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="AI confidence in the recommendation accuracy (0.0-1.0)",
    )


RESPONSE_SCHEMA_JSON = json.dumps(AIRecommendationSchema.model_json_schema(), indent=2)


class AIRecommender:
    """
    Sinh AI recommendation dùng Gemini 2.5 Flash.

    Features:
    - Structured output (native JSON mode) — không cần parse markdown
    - 2 prompt strategies: basic vs context_enriched
    - Latency tracking cho thực nghiệm
    - Retry logic với exponential backoff
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        logger.info("AIRecommender initialized: model=%s", model)

    async def recommend(
        self,
        finding: UnifiedComplianceFinding,
        strategy: Literal["basic", "context_enriched"] = "context_enriched",
    ) -> AIRecommendation:
        """
        Sinh AI recommendation cho finding.

        Args:
            finding: UnifiedComplianceFinding cần recommend
            strategy: "basic" hoặc "context_enriched" (cho thực nghiệm)

        Returns:
            AIRecommendation với structured output từ Gemini
        """
        prompt = self._build_prompt(finding, strategy)

        start_time = time.perf_counter()
        try:
            response = await self._call_gemini(prompt)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Parse structured output
            rec_data = AIRecommendationSchema.model_validate_json(response.text)

            result = AIRecommendation(
                finding_id=finding.finding_id,
                strategy_used=strategy,
                model=self.model,
                root_cause=rec_data.root_cause,
                yaml_fix=rec_data.yaml_fix,
                impact_if_unfixed=rec_data.impact_if_unfixed,
                cis_references=rec_data.cis_references,
                urgency=rec_data.urgency,
                confidence=rec_data.confidence,
                latency_ms=round(latency_ms, 2),
            )

            logger.info(
                "AI recommendation generated: finding=%s strategy=%s latency=%.1fms confidence=%.2f",
                finding.finding_id,
                strategy,
                latency_ms,
                rec_data.confidence,
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "AI recommendation failed: finding=%s strategy=%s error=%s latency=%.1fms",
                finding.finding_id,
                strategy,
                e,
                latency_ms,
            )
            raise

    async def recommend_both_strategies(
        self,
        finding: UnifiedComplianceFinding,
    ) -> dict[str, AIRecommendation]:
        """
        Sinh cả 2 strategies cho thực nghiệm so sánh.

        Returns:
            {"basic": AIRecommendation, "context_enriched": AIRecommendation}
        """
        import asyncio

        basic_task = self.recommend(finding, "basic")
        enriched_task = self.recommend(finding, "context_enriched")

        results = await asyncio.gather(basic_task, enriched_task, return_exceptions=True)

        output = {}
        if not isinstance(results[0], Exception):
            output["basic"] = results[0]
        if not isinstance(results[1], Exception):
            output["context_enriched"] = results[1]

        return output

    def _build_prompt(
        self,
        finding: UnifiedComplianceFinding,
        strategy: str,
    ) -> str:
        """Build prompt theo strategy."""
        kwargs = dict(
            finding_id=finding.finding_id,
            resource_kind=finding.resource.kind,
            resource_name=finding.resource.name,
            namespace=finding.resource.namespace or "cluster-wide",
            title=finding.title,
            severity=finding.severity.value,
            source=finding.source,
            description=finding.description,
            response_schema=RESPONSE_SCHEMA_JSON,
        )

        if strategy == "basic":
            return build_basic_prompt(**kwargs)
        else:  # context_enriched
            return build_context_enriched_prompt(**kwargs)

    async def _call_gemini(self, prompt: str) -> types.GenerateContentResponse:
        """
        Call Gemini API với JSON response mode.

        Note: google-genai v1.0+ dùng async via asyncio.
        """
        import asyncio

        # Gemini 2.5 Flash với native JSON structured output
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIRecommendationSchema,
                    temperature=0.1,  # Low temperature for more deterministic output
                    max_output_tokens=2048,
                ),
            ),
        )
        return response

    # -------------------------------------------------------------------------
    # Part 2: Batch / Summary / Remediation methods
    # -------------------------------------------------------------------------

    async def generate_summary(
        self,
        findings: list[UnifiedComplianceFinding],
        score_result,  # ScoreResult — avoid circular import
    ) -> AISummary:
        """
        Generate AI executive summary từ toàn bộ findings + score.

        Dùng EXECUTIVE_SUMMARY_PROMPT để ask Gemini tổng hợp security posture
        và sinh top 3 priorities + 3-phase remediation roadmap.

        Returns:
            AISummary với overall_assessment, risk_level, top_priorities, phases
        """
        import json as _json

        # Build findings summary text (top 10 failed findings)
        failed = [f for f in findings if f.status.value == "fail"][:10]
        findings_summary = "\n".join(
            f"- [{f.severity.value.upper()}] {f.finding_id}: {f.title} ({f.source})"
            for f in failed
        )

        # Domain scores formatted
        domain_scores_text = "\n".join(
            f"  - {d.domain.value}: {d.score:.1f}/100 (weight: {d.weight*100:.0f}%)"
            for d in score_result.domains
        )

        # Severity counts
        sev_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in failed:
            sv = f.severity.value
            if sv in sev_counts:
                sev_counts[sv] += 1

        response_schema = _json.dumps(AISummary.model_json_schema(), indent=2)

        prompt = build_executive_summary_prompt(
            overall_score=score_result.overall_score,
            classification=score_result.classification.value,
            domain_scores=domain_scores_text,
            total_findings=len(findings),
            critical=sev_counts["critical"],
            high=sev_counts["high"],
            medium=sev_counts["medium"],
            low=sev_counts["low"],
            findings_summary=findings_summary,
            response_schema=response_schema,
        )

        start_time = time.perf_counter()
        try:
            response = await self._call_gemini_with_schema(prompt, AISummary)
            latency_ms = (time.perf_counter() - start_time) * 1000

            summary = AISummary.model_validate_json(response.text)
            summary.latency_ms = round(latency_ms, 2)

            logger.info(
                "AI summary generated: risk=%s latency=%.1fms findings=%d",
                summary.risk_level,
                latency_ms,
                len(findings),
            )
            return summary

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("AI summary generation failed: error=%s latency=%.1fms", e, latency_ms)
            raise

    async def generate_remediation_plan(
        self,
        findings: list[UnifiedComplianceFinding],
    ) -> RemediationPlan:
        """
        Generate prioritized remediation plan từ findings.

        Organizes findings into 3 phases:
          - immediate: CRITICAL severity
          - this_sprint: HIGH severity
          - backlog: MEDIUM/LOW severity

        Returns:
            RemediationPlan với phased approach và effort estimates
        """
        import json as _json

        failed = [f for f in findings if f.status.value == "fail"]
        violations_detail = "\n".join(
            f"- [{f.severity.value.upper()}] {f.finding_id}: {f.title}\n"
            f"  Resource: {f.resource.kind}/{f.resource.name} | Source: {f.source}\n"
            f"  Description: {f.description[:200]}"
            for f in failed[:20]  # limit to 20 findings
        )

        response_schema = _json.dumps(RemediationPlan.model_json_schema(), indent=2)
        prompt = build_remediation_plan_prompt(
            violations_detail=violations_detail,
            response_schema=response_schema,
        )

        start_time = time.perf_counter()
        try:
            response = await self._call_gemini_with_schema(prompt, RemediationPlan)
            latency_ms = (time.perf_counter() - start_time) * 1000

            plan = RemediationPlan.model_validate_json(response.text)
            plan.total_findings = len(failed)
            plan.latency_ms = round(latency_ms, 2)

            logger.info(
                "Remediation plan generated: phases=%d findings=%d latency=%.1fms",
                len(plan.phases),
                len(failed),
                latency_ms,
            )
            return plan

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Remediation plan generation failed: error=%s latency=%.1fms", e, latency_ms)
            raise

    async def _call_gemini_with_schema(
        self,
        prompt: str,
        schema,
    ):
        """Call Gemini API với arbitrary response schema."""
        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            ),
        )
        return response

    async def health_check(self) -> bool:
        """Kiểm tra Gemini API connection."""
        try:
            loop = __import__("asyncio").get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents="Respond with: OK",
                    config=types.GenerateContentConfig(max_output_tokens=5),
                ),
            )
            return True
        except Exception as e:
            logger.warning("Gemini health check failed: %s", e)
            return False

