# IDP Platform — Minimal Internal Developer Platform on Amazon EKS

> **Đề tài:** Thiết kế và triển khai Internal Developer Platform tối giản trên Amazon EKS theo mô hình GitOps tích hợp Continuous Compliance Scorecard và hỗ trợ khuyến nghị khắc phục bằng AI cho Kubernetes Workloads

## Cấu trúc repo

```
idp-platform/
├── infrastructure/          # Terraform IaC (VPC, EKS, ECR)
│   ├── 01-network/
│   ├── 02-cluster-eks/
│   └── 03-ecr/
├── idp-gitops/              # GitOps repo — ArgoCD source of truth
│   ├── argocd/              # App-of-Apps definitions
│   ├── apps/                # Per-service Helm values
│   ├── charts/              # Shared Helm chart
│   └── platform/            # Add-ons (monitoring, kyverno, trivy...)
├── idp-microservices/       # Application source code (5 services)
│   ├── .github/workflows/   # GitHub Actions CI pipelines
│   └── src/                 # Java, Go, NestJS source
├── backstage/               # Backstage IDP portal (EC2-hosted)
├── compliance-engine/       # Python/FastAPI Compliance Scorecard engine
└── docs/                    # Architecture diagrams, research notes
```

## Setup

👉 Xem [**SETUP.md**](SETUP.md) — Hướng dẫn chi tiết từng bước setup toàn bộ dự án.

## Milestones

| Milestone | Mô tả | Code | Deploy |
|---|---|---|---|
| **M1: Foundation** | GitHub Actions CI + GitOps pipeline E2E | ✅ Done | ⏳ Chưa deploy |
| **M2: IDP Core** | Backstage portal + Golden Path Template | ✅ Done (thiếu scaffold) | ⏳ Chưa deploy |
| **M3: Compliance** | Scorecard Framework + AI Recommendation | ✅ Done | ⏳ Chưa deploy |

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud | AWS (`us-east-1`) |
| Kubernetes | Amazon EKS 1.31 |
| IaC | Terraform |
| GitOps | Argo CD |
| CI | GitHub Actions |
| Registry | Amazon ECR |
| Portal | Backstage (on EC2) |
| Policy | Kyverno |
| Scan | Trivy Operator |
| Compliance | kube-bench + custom engine |
| Compliance API | FastAPI + PostgreSQL |
| AI | Gemini/OpenAI API |
| Monitoring | Prometheus + Grafana + Loki |

## Kiến trúc (PE-RM 4-Layer)

```
Experience:    Backstage Portal | Software Templates | Compliance Dashboard
Delivery:      GitHub Actions   | Argo CD (GitOps)   | Compliance Engine
Runtime:       Amazon EKS       | Kyverno            | Trivy Operator
Infrastructure: AWS VPC/EC2/IAM | Terraform          | Amazon ECR
```
