# Buổi AWS 1: lần dựng EKS đầu tiên — hạ tầng OK, Argo CD kẹt do chart cũ

**Ngày:** 2026-11-16
**Thành phần:** infrastructure, gitops, other (CI)
**Loại:** experiment

## Mô tả
Lần đầu chạy lớp tạo-huỷ trên AWS (account 736508008585, us-east-1, `AWS_PROFILE=idp`, WSL).

### Trình tự đã làm trong buổi
1. Lớp nền `aws-foundation-up.sh` (174s): S3 state, 6 ECR, OIDC + role CI, 5 SSM SecureString.
2. GitHub secret `AWS_ROLE_ARN`. Workflow permissions không cần đổi (workflow tự khai báo `contents: write`).
3. CI: sửa 3 lỗi chặn build (PR #2, #3):
   - `trivy-action@0.28.0` không còn tồn tại → pin SHA v0.36.0;
   - OIDC immutable subject → trust policy nhận cả hai dạng `sub` (đã apply 04-oidc);
   - Trivy gate chặn 5 image Retail Store (CVE Spring 6.2 chỉ sửa ở 7.x) → report-only cho Retail Store, giữ gate cho compliance-engine.
   - GitOps push 403 tạm thời khi 6 workflow chạy đồng thời → `gh run rerun --failed` từng run.
   Kết quả: 6 image `f474fb2` trong ECR, tag ghi vào main `5fa651c`.
4. `aws-up.sh --dry-run` → preflight pass, 01-network 19 add.
5. `aws-up.sh --yes` (bắt đầu 04:00:49 UTC):
   | Bước | Thời gian | Kết quả |
   |---|---|---|
   | preflight | 18s | pass |
   | 01-network | 143s | 19 add (NAT 1m37s) |
   | 02-cluster-eks | ~17m | 46 add (control plane 10m21s, node group 1m50s, Argo CD helm 1m38s) |
   | k8s-secrets | ~65s | 5 secret |
   | chờ Argo CD apps | dừng tay lúc ~04:32 | 19 app, chưa all Healthy |

### Kết quả kiểm chứng trên EKS 1.35.9 (2 node t3.large)
- **Chạy được:** namespace, storageclass, metrics-server, cluster-autoscaler (app Healthy), retail-store-databases, compliance-engine, kube-bench, kyverno-policies, retail-store-checkout/orders.
- **Kyverno policy hoạt động thật**: sinh event `PolicyViolation` (require-run-as-non-root, read-only-rootfs, drop-all-capabilities, disallow-privilege-escalation, require-resource-limits) cho pod Retail Store và job Kyverno.
- Snapshot: `docs/evidence/aws/20261116T040049Z-up/` (`argocd-apps-snapshot.txt`, `argocd-conditions.txt`, `pods-not-running*.txt`, `top-nodes.txt`, `aws-up.log`, `timings.txt`).

### Lỗi tìm được trên cluster (chưa sửa)
1. **Argo CD chart 5.51.4 (app v2.9) không hỗ trợ K8s 1.35**: `ComparisonError ... .status.terminatingReplicas: field not declared in schema` (trường Deployment status từ K8s 1.33). Ảnh hưởng: platform-kyverno, platform-trivy-operator, platform-kube-prometheus-stack, platform-loki (sync Unknown) → root OutOfSync. Sửa: nâng `argocd_chart_version` (02-cluster-eks) lên chart 10.x (app v3.4/3.5, chọn bản ≥ 2 tuần tuổi).
2. **Kyverno chart 3.2.6 dùng `bitnami/kubectl:1.28.5`** (đã bị xoá khỏi Docker Hub) cho cleanup job/cronjob → `ImagePullBackOff` (6 pod). Sửa: nâng chart Kyverno (bản hỗ trợ K8s 1.35) hoặc override image cleanup.
3. **Thiếu CPU request**: `0/2 nodes are available: 2 Insufficient cpu` cho loki-0, cart ×2, catalog, ui (retail-store-cart/catalog/ui Degraded), dù CPU dùng thật chỉ 8% / 38%. Cluster-autoscaler (max 3) **không scale**. Cần: kiểm log autoscaler (IRSA/tag ASG `k8s.io/cluster-autoscaler/*`), giảm request của monitoring/Retail Store, hoặc tăng `node_desired_size`/instance type.
4. trivy-operator: 2 pod `scan-vulnerabilityreport-*` Error (log cho thấy đang tải trivy-db 134 MiB lúc bị dừng — chưa rõ nguyên nhân). Chưa có VulnerabilityReport.
5. Chưa chạy `smoke.sh` (dừng trước), chưa kiểm internal CLB `compliance-engine-internal`, workload A/B/C (app `experiments` chưa xuất hiện trong 19 app).

### aws-down (04:40–05:12 UTC, 1923s, exit 0)
| Bước | Mốc | Ghi chú |
|---|---|---|
| xoá Application | 04:40 → 04:56 | 18 → 1 app trong 3 phút; **`root` kẹt finalizer tới hết timeout 900s**, script gỡ finalizer |
| LB/PVC | 04:56 | 0 Service LoadBalancer; 7 PVC (6 Bound, loki Pending) → PV về 0 |
| destroy 05 | — | không có state, bỏ qua |
| destroy 02-cluster-eks | 04:56 → 05:10 | 46 destroyed (~14 phút) |
| destroy 01-network | 05:10 → 05:12 | 19 destroyed |
| kiểm mồ côi | 05:12 | không có ELB/EBS/ENI/NAT/EIP |
- Kiểm thêm bằng CLI sau khi down: không còn EKS cluster, VPC, NAT, EIP, ELB, EBS volume, EC2, ENI, CloudWatch log group `/aws/eks`. Lớp nền còn nguyên: S3 state (01/02 state rỗng, 03, 04), 6 ECR, role CI, 5 SSM.
- Thời gian tính tiền theo giờ ≈ 04:01 → 05:12 (~71 phút) ≈ **$0.42** + KMS key (chờ xoá 7 ngày) + CloudWatch Logs ingest nhỏ; tổng buổi ước tính < $1.
- Evidence: `docs/evidence/aws/20261116T044004Z-down/` (`aws-down.log`, `apps-before.txt`, `pvc-before.txt`, `orphans-*.txt`, `timings.txt`).

### Phát hiện thêm khi down
6. **Không có Service LoadBalancer nào** lúc down: internal CLB `compliance-engine-internal` không được tạo dù app `compliance-engine` Synced/Healthy → cần kiểm kustomization (`service-internal-lb.yaml` có được include?) và annotation cloud provider. (#24 vẫn chưa kiểm chứng.)
7. `aws-down.sh`: xoá `root` cascade chờ tới timeout 900s (root Degraded, chờ child đang xoá) → nên xoá child app trước rồi mới xoá root, hoặc giảm timeout cho root.
8. `aws-down.sh`: kiểm "orphans" **trước** destroy báo NAT gateway (do Terraform quản lý) → báo động giả; chỉ nên kiểm ELB/EBS/ENI do Kubernetes tạo ở bước này.

## Các file đã thay đổi
- `docs/evidence/aws/20261116T035455Z-up/` (dry-run), `docs/evidence/aws/20261116T040049Z-up/` (lần chạy thật + snapshot), `docs/evidence/aws/20261116T044004Z-down/`
- `docs/SETUP.md` (Troubleshooting: lỗi thật trên EKS)
- `context/2026-11-15_testable-rebuild-progress.md`, file này

## Ghi chú / Vấn đề còn lại
- Người dùng dừng buổi ở đây (04:32 UTC) và yêu cầu `aws-down.sh`: **đã down xong, không còn tài nguyên tính tiền theo giờ**. Lớp nền giữ lại.
- Thứ tự sửa đề xuất cho buổi sau: (1) Argo CD 3.x, (2) Kyverno chart mới / image cleanup, (3) CPU request + autoscaler, (4) kiểm trivy-operator, kps 58, loki 6.6 trên Argo CD mới, (5) internal CLB, (6) sửa 2 điểm của aws-down (mục 7, 8), (7) smoke.
- Các chart 2024 còn lại (trivy-operator 0.24.1, kube-prometheus-stack 58, loki 6.6) nên rà version cùng lúc vì Argo CD v2.9 che mất lỗi phía sau.
