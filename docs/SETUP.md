# SETUP — IDP Compliance Scorecard

Runbook xoay quanh script. Hạ tầng có hai lớp:

| Lớp | Gồm | Vòng đời | Script |
|---|---|---|---|
| **Nền** | S3 state bucket, ECR (6 repo), GitHub OIDC + IAM role CI, SSM Parameter Store | tạo một lần, **không** destroy | `scripts/aws-foundation-up.sh` |
| **Tạo-huỷ** | VPC + NAT, EKS + node group, Argo CD + root app, (tuỳ chọn) Backstage EC2 | mỗi buổi lab | `scripts/aws-up.sh` / `scripts/aws-down.sh` |

> Trạng thái: các bước dưới đây đã kiểm tĩnh (validate-local). Chưa chạy trên AWS và chưa chạy CI. Mục nào chưa kiểm chứng thì ghi rõ. Danh sách lệch gốc: `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`. Tiến độ: `context/2026-11-15_testable-rebuild-progress.md`.

## 1. Prerequisites

### Máy dev (Windows, chỉ chạy lệnh nhẹ)
Tool ở `C:\tools\*`. Không cài kubectl/helm/kind trên máy.

| Tool | Version | Kiểm tra |
|---|---|---|
| Git Bash | 2.56 | `git --version` |
| Python | 3.12 | `py -3.12 --version` |
| Node | 20.18.0 | `/c/tools/node/node --version` |
| terraform | 1.11.4 | `/c/tools/terraform/terraform version` |
| tflint | 0.53.0 | `/c/tools/tflint/tflint --version` |
| gh | 2.62.0 | `/c/tools/gh/bin/gh --version` |
| aws-cli | 2.22.0 | `/c/tools/awscli/Amazon/AWSCLIV2/aws --version` |
| WSL Ubuntu-22.04 | terraform 1.11.4 + tflint 0.53.0 trong `~/tools/bin` | `wsl -d Ubuntu-22.04 -- ~/tools/bin/terraform version` |

Windows Application Control chặn `terraform-provider-*.exe`, nên `terraform validate`/`tflint` trên máy chạy trong WSL (script tự gọi).

Lần đầu:

```bash
cd compliance-engine && py -3.12 -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
```

```bash
cd backstage/plugins/compliance-scorecard && npm ci --ignore-scripts --legacy-peer-deps
```

### Nơi chạy script AWS
AWS CloudShell (us-east-1) hoặc một máy Linux có aws-cli v2. Script cần terraform và kubectl. Trong CloudShell:

```bash
git clone https://github.com/tranduyloc895/idp-compliance-scorecard.git && cd idp-compliance-scorecard
```

```bash
bash scripts/cloudshell-tools.sh && export PATH=$HOME/bin:$PATH
```

Nếu không có kubectl mà có Docker, script chạy kubectl qua image `alpine/k8s:1.35.0`.

## 2. Kiểm tra trước khi tốn tiền

```bash
bash scripts/validate-local.sh
```

Gồm: chặn placeholder/account ID/region sai, YAML, cú pháp shell + LF, terraform fmt/validate/tflint (WSL), pytest, tsc. Lần chạy gần nhất trên máy: PASS, khoảng 32 giây.

CI (`.github/workflows/validate.yml`) chạy thêm phần nặng: helm/kustomize/kubeconform có CRD schema, render chart upstream, `kyverno test` 8 policy × workload A/B/C, kiểm image tag tồn tại, `docker build` 6 image, `engine-smoke` (docker compose + fixture + contract-check). Đọc kết quả:

```bash
gh run list --branch feat/testable-rebuild --limit 5
```

```bash
gh run view <run-id> --log-failed
```

Artifact `engine-smoke-evidence` và `rendered-manifests` tải ở trang run.

## 3. Lớp nền (một lần)

```bash
bash scripts/aws-foundation-up.sh --dry-run
```

```bash
bash scripts/aws-foundation-up.sh
```

Script làm theo thứ tự: `00-bootstrap` (bucket `idp-tfstate-<account>-us-east-1`, state local, tự import nếu bucket đã có) → `03-ecr` → `04-oidc` (tự tắt tạo OIDC provider nếu account đã có) → `ssm-put-secrets.sh`.

Secret: copy `scripts/secrets.env.example` thành `scripts/secrets.env` (git ignore) nếu muốn tự đặt giá trị. Để trống thì mật khẩu tự sinh. `GEMINI_API_KEY` và `TELEGRAM_BOT_TOKEN` là tuỳ chọn. Tham số lưu ở `/idp/...` dạng SecureString. Ghi đè bằng `--overwrite`.

Sau đó làm tay một lần:
1. GitHub → Settings → Secrets → Actions: `AWS_ROLE_ARN` = output `role_arn` mà script in ra. `GITOPS_TOKEN` là tuỳ chọn; nếu không đặt, CI dùng `GITHUB_TOKEN` và cần Workflow permissions = Read and write.
2. Chạy workflow **build-all** trên nhánh Argo CD theo dõi (`main`). CI ghi registry vào `idp-gitops/apps/image-registry.yaml` và tag vào `apps/<svc>/values.yaml` cùng `compliance/compliance-engine/kustomization.yaml`. Đây là các file "MANAGED BY CI".

## 4. Vòng lab

```bash
bash scripts/aws-up.sh --dry-run
```

```bash
bash scripts/aws-up.sh
```

1. **Preflight:** có state bucket và ECR; registry trong GitOps khớp account; mọi tag có trong ECR. Fail thì dừng trước khi tạo tài nguyên tốn tiền.
2. `01-network` → `02-cluster-eks` (EKS 1.35, Argo CD, root Application).
3. `k8s-secrets.sh`: tạo Secret từ SSM.
4. Chờ mọi Argo CD Application Synced/Healthy.
5. Ghi DNS internal LB của engine vào SSM `/idp/backstage/compliance-engine-url`.
6. `smoke.sh`.
7. In lệnh port-forward.

Thêm `--with-backstage` để dựng EC2 Backstage. Repo chưa có `packages/app` và `packages/backend` (audit #22), nên image Backstage chưa build được. `--skip-smoke` để bỏ bước smoke.

Truy cập (từ CloudShell hoặc máy có kubectl):

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:80
```

```bash
kubectl -n compliance port-forward svc/compliance-engine 8000:8000
```

```bash
kubectl -n retail-store port-forward svc/ui 8081:80
```

Gọi scan thủ công. Phải có body (audit #15):

```bash
curl -X POST http://localhost:8000/api/v1/scans -H 'Content-Type: application/json' -d '{"namespace":"compliance-test"}'
```

Rồi poll `GET /api/v1/scans/<id>` tới `completed`.

**Kết thúc buổi lab, luôn chạy:**

```bash
bash scripts/aws-down.sh
```

Thứ tự: xoá root Application (cascade) → xoá Service LoadBalancer và PVC, chờ PV hết → destroy `05` → `02` → `01` → kiểm ELB/ENI/EBS/NAT/EIP mồ côi. Không đụng lớp nền.

Evidence mỗi lần chạy nằm trong `docs/evidence/aws/<timestamp>-<up|smoke|down>/` (timings, response API, image digest).

## 5. Khi bị dừng giữa chừng

1. Xem còn gì: `bash scripts/aws-down.sh --dry-run`. Lệnh này liệt kê Application/LB/PVC, chạy `plan -destroy` từng module và kiểm tài nguyên mồ côi.
2. Chạy lại `bash scripts/aws-down.sh`. Script idempotent và bỏ qua module không có state.
3. Kiểm AWS Console (us-east-1): EC2 → Load Balancers, Volumes (status *available*), Network Interfaces, Elastic IPs; VPC → NAT Gateways; EKS → Clusters.
4. Nếu `terraform destroy 01-network` kẹt ở subnet/IGW: thường còn ELB hoặc ENI do Kubernetes tạo. Xoá tay theo `orphans-*.txt` rồi chạy lại.

## 6. Troubleshooting

Chỉ ghi các lỗi **đã gặp thật** trong quá trình làm. Lỗi trên AWS sẽ bổ sung sau lần chạy đầu.

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `terraform validate` báo *An Application Control policy has blocked this file* | Windows chặn provider `.exe` | Dùng `scripts/validate-local.sh` (tự chạy qua WSL) |
| `wsl.exe ... bash -c "export PATH=$HOME..."` lỗi cú pháp | `wsl.exe` tự expand `$VAR` của Windows | Gọi thẳng file script: `wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/.../scripts/terraform-validate.sh` |
| Đường dẫn `/mnt/c/...` bị đổi thành `C:/tools/git-bash/...` | MSYS path conversion | `MSYS_NO_PATHCONV=1` |
| `pip install -e .[dev]` lỗi `setuptools.backends.legacy` | build-backend sai (#13) | Đã sửa: `setuptools.build_meta` |
| `tsc`: `Property 'gap' does not exist on type BoxProps` | MUI v4 `Box` không có prop `gap` | Đã sửa: `style={{ gap: 8 }}` |
| Script bash lỗi `$'\r'` trên Linux | CRLF từ Windows | `.gitattributes` ép LF; validate-local kiểm CRLF |

## 7. Chi phí (cấu hình thật trong Terraform, us-east-1)

Giá tham khảo theo bảng giá công khai, **chưa đối chiếu lại với giá hôm nay**. Kiểm lại bằng AWS Pricing Calculator trước khi báo cáo. Không gồm thuế và data transfer.

### Theo giờ (chỉ khi lớp tạo-huỷ đang chạy)

| Thành phần | Cấu hình (file) | Đơn giá ước tính | $/giờ |
|---|---|---|---|
| EKS control plane | 1 cluster, K8s 1.35, standard support (`02/variables.tf`) | $0.10/h | 0.100 |
| Worker node | 2 × t3.large ON_DEMAND (`node_desired_size=2`, max 3) | $0.0832/h/node | 0.166 |
| NAT Gateway | 1 (`single_nat_gateway=true`) | $0.045/h + $0.045/GB | 0.045 |
| Public IPv4 | EIP của NAT | $0.005/h | 0.005 |
| Internal Classic LB | `compliance-engine-internal` (LB duy nhất) | ~$0.025/h | 0.025 |
| EBS gp3 | 2×30 GB node + ~51 GB PVC (Prometheus 20, Loki 10, Grafana 5, MariaDB 5, Postgres 5, compliance 2, Alertmanager 2, DynamoDB-local 1, Redis 1) ≈ 111 GB | $0.08/GB-tháng | ~0.012 |
| CloudWatch Logs | control plane api/audit/authenticator, giữ 7 ngày | $0.50/GB ingest | biến đổi |
| KMS key | 1 key/cluster (xoá sau 7 ngày) | $1/tháng | ~0.001 |
| **Tổng (không Backstage)** | | | **≈ $0.35/giờ** (4 giờ lab ≈ $1.4) |
| + Backstage EC2 (`--with-backstage`) | t3.small + 20 GB gp3 + EIP | $0.0208 + ~0.002 + 0.005 | +0.028 |

Giảm chi phí: `TF_VAR_node_capacity_type=SPOT`; khi đó node t3.large thường còn khoảng 30–40% giá on-demand và có thể bị thu hồi. Hoặc dùng `TF_VAR_node_desired_size=1`, nhưng một node có thể không đủ cho monitoring stack. **Không** dùng K8s 1.31 hoặc các bản đã hết standard support: phí control plane extended support là $0.60/giờ.

### Gần 0 (lớp nền, giữ lại)

| Thành phần | Ước tính/tháng |
|---|---|
| S3 state (vài trăm KB, versioning, xoá version cũ sau 90 ngày) | < $0.01 |
| ECR: 6 repo, giữ 10 image/repo (Java khoảng 300 MB/image) | $0.2–1.8 ($0.10/GB) |
| SSM Parameter Store standard + SecureString (key `aws/ssm`) | $0 |
| IAM role, OIDC provider | $0 |

## 8. Cấu trúc liên quan

```
infrastructure/00-bootstrap   S3 state (state local)            — nền
infrastructure/03-ecr         6 repo ECR                         — nền
infrastructure/04-oidc        GitHub OIDC + role CI              — nền
infrastructure/01-network     VPC, NAT                           — tạo-huỷ
infrastructure/02-cluster-eks EKS, IRSA, Argo CD + root app      — tạo-huỷ
infrastructure/05-backstage-ec2  Backstage host (tuỳ chọn)       — tạo-huỷ
idp-gitops/argocd             Application (wave -10 → 15)
scripts/                      validate-local, aws-*, smoke, k8s-secrets, ssm-put-secrets
```
