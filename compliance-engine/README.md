# Compliance Engine

Python/FastAPI backend cho Continuous Compliance Scorecard Framework.
Sẽ được triển khai trong Milestone 3.

## Modules (planned)
- `collector/` — Thu thập data từ Kyverno, Trivy Operator, kube-bench
- `normalizer/` — Transform về Unified Compliance Finding schema
- `scorer/` — Weighted scoring engine (4 domains)
- `recommender/` — Rule-based + AI-assisted recommendations
- `api/` — FastAPI REST API
