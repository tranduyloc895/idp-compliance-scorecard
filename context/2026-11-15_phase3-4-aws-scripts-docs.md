# Giai đoạn 3–4 — Script AWS và tài liệu

**Ngày:** 2026-11-15
**Thành phần:** infrastructure, docs, other (scripts)
**Loại:** feature

## Mô tả
- `scripts/lib.sh` (dùng chung), `aws-foundation-up.sh`, `aws-up.sh`, `aws-down.sh`, `smoke.sh`, `k8s-secrets.sh`, `ssm-put-secrets.sh`, `cloudshell-tools.sh`; tất cả có `--dry-run` (terraform plan / liệt kê, không tạo gì).
- aws-up có preflight chặn trước khi tốn tiền (state bucket, ECR, registry/tag GitOps khớp image trong ECR). aws-down đúng thứ tự: root app cascade → LB/PVC → destroy 05/02/01 → kiểm ELB/ENI/EBS/NAT/EIP mồ côi; không đụng lớp nền.
- EKS 1.31 → 1.35: 1.31 đã hết standard support (extended $0.60/h, hết hẳn cuối 11/2026); 1.35 standard tới 2027-03-27 (nguồn: docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html). Cluster-autoscaler v1.35.0, kubectl v1.35.0, image kubectl `alpine/k8s:1.35.0` (tag bitnami cũ ngừng phát hành). CI thêm kiểm image tag tồn tại.
- `docs/SETUP.md` viết lại quanh script, có bảng chi phí theo cấu hình Terraform thật (≈ $0.35/giờ không Backstage).

## Các file đã thay đổi
- `scripts/{lib,aws-foundation-up,aws-up,aws-down,smoke,k8s-secrets,ssm-put-secrets,cloudshell-tools}.sh`, `scripts/secrets.env.example`
- `docs/SETUP.md`, `docs/evidence/aws/README.md`, `infrastructure/README.md`, `infrastructure/04-oidc/README.md`
- `infrastructure/02-cluster-eks/variables.tf`, `idp-gitops/platform/cluster-autoscaler/values.yaml`, `idp-gitops/platform/kube-bench/cronjob.yaml`, `scripts/k8s-render-check.sh`

## Ghi chú / Vấn đề còn lại
- Kiểm chứng trên máy: `bash -n` + LF cho mọi script; 4 script chạy `--dry-run` khi tắt hết credential → dừng đúng ở STS với thông báo rõ. **Chưa chạy với AWS** (chờ đồng ý dùng credential / chạy aws-up).
- Argo CD đồng bộ từ GitHub `main` (child Application ghi `targetRevision: main`): kiểm thử EKS cần nội dung branch đã lên `main` (hoặc tạm đổi targetRevision).
- Chưa kiểm chứng, lỗi dự kiến khi lên EKS: chart 2024 (kyverno 3.2.6, trivy-operator 0.24.1, kps 58, loki 6.6, Argo CD 5.51.4) trên K8s 1.35; CLB internal qua cloud provider của EKS 1.35; `kube-bench v0.8.0 --benchmark eks-1.2.0`; tag `cluster-autoscaler v1.35.0`, `alpine/k8s:1.35.0`; tài nguyên 2× t3.large cho monitoring stack; thời gian Trivy sinh VulnerabilityReport; phiên CloudShell timeout khi tạo EKS (~15 phút).
- Bảng giá chưa đối chiếu với giá ngày hiện tại.
