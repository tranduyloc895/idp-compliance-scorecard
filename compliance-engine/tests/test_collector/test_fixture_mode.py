"""COLLECTOR_MODE=fixtures: aggregator đọc file JSON scenario A/B/C, không cần cluster."""

from __future__ import annotations

from pathlib import Path

from app.collector.aggregator import ComplianceAggregator
from app.normalizer.mapper import NormalizerMapper
from app.scorer.engine import ComplianceScorer

SCENARIO = Path(__file__).parents[2] / "fixtures" / "scenario-abc"


async def test_fixture_aggregator_collects_all_three_sources():
    agg = ComplianceAggregator(None, fixtures_dir=str(SCENARIO))
    raw = await agg.collect_all()
    sources = {r.source for r in raw}
    assert sources == {"kyverno", "trivy", "kube-bench"}
    # 3 workload x 8 policy + 5 CVE + 5 CIS
    assert len(raw) == 24 + 5 + 5


async def test_fixture_namespace_filter():
    agg = ComplianceAggregator(None, fixtures_dir=str(SCENARIO))
    raw = await agg.collect_all("other-namespace")
    # kube-bench luôn cluster-wide; Kyverno/Trivy bị lọc hết
    assert {r.source for r in raw} == {"kube-bench"}


async def test_fixture_pipeline_scores_workload_a_below_b():
    agg = ComplianceAggregator(None, fixtures_dir=str(SCENARIO))
    unified = NormalizerMapper().normalize_all(await agg.collect_all())
    by_workload = {
        name: [f for f in unified if f.resource.name.startswith(name)]
        for name in ("workload-a-poor", "workload-b-excellent", "workload-c-fair")
    }
    scorer = ComplianceScorer()
    scores = {k: scorer.calculate(v, scan_id=1).overall_score for k, v in by_workload.items()}
    assert scores["workload-a-poor"] < scores["workload-c-fair"] < scores["workload-b-excellent"]
