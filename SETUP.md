# 🚀 Hướng dẫn Setup — IDP Platform trên Amazon EKS

> **Đề tài:** Thiết kế và triển khai Internal Developer Platform tối giản trên Amazon EKS theo mô hình GitOps tích hợp Continuous Compliance Scorecard và hỗ trợ khuyến nghị khắc phục bằng AI cho Kubernetes Workloads

Hướng dẫn này mô tả **từng bước** để setup và deploy toàn bộ IDP Platform từ đầu.

---

## Mục lục

- [Prerequisites](#prerequisites)
- [Phase 1 — Infrastructure (Terraform + EKS)](#phase-1--infrastructure-terraform--eks)
- [Phase 2 — GitOps Bootstrap (ArgoCD)](#phase-2--gitops-bootstrap-argocd)
- [Phase 3 — Backstage IDP Portal (EC2)](#phase-3--backstage-idp-portal-ec2)
- [Phase 4 — Compliance Engine (Local Dev)](#phase-4--compliance-engine-local-dev)
- [Phase 5 — Compliance Engine (EKS Deploy)](#phase-5--compliance-engine-eks-deploy)
- [Phase 6 — Experiment Workloads](#phase-6--experiment-workloads)
- [Phase 7 — GitHub Actions CI Pipeline](#phase-7--github-actions-ci-pipeline)
- [Tear Down (Hủy hạ tầng)](#tear-down)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Tools cần cài trên máy local

| Tool | Version | Cài đặt |
|---|---|---|
| **Terraform** | ≥ 1.5.0 | [terraform.io/downloads](https://developer.hashicorp.com/terraform/downloads) |
| **AWS CLI** | v2 | [docs.aws.amazon.com/cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **kubectl** | ≥ 1.28 | [kubernetes.io/docs/tasks/tools](https://kubernetes.io/docs/tasks/tools/) |
| **Docker** | ≥ 24.0 | [docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | v2 | Đi kèm Docker Desktop |
| **Node.js** | ≥ 20 LTS | [nodejs.org](https://nodejs.org/) (cho Backstage scaffold) |
| **Git** | ≥ 2.40 | [git-scm.com](https://git-scm.com/) |
| **Python** | ≥ 3.11 | [python.org](https://www.python.org/) (cho Compliance Engine dev) |

### AWS Account setup

```bash
# 1. Cấu hình AWS CLI với credentials
aws configure
# AWS Access Key ID:     <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name:   us-east-1
# Default output format: json

# 2. Verify
aws sts get-caller-identity
```

### Terraform S3 Backend

Tạo S3 bucket cho Terraform state (chạy 1 lần):

```bash
aws s3 mb s3://devsecops-tfstate-23520868-23521463 --region us-east-1
aws s3api put-bucket-versioning \
  --bucket devsecops-tfstate-23520868-23521463 \
  --versioning-configuration Status=Enabled
```

### GitHub Repositories

Push code lên 3 GitHub repos (nếu chưa có):

```bash
# Repo 1: Infrastructure
cd idp-platform/infrastructure
git init && git remote add origin https://github.com/tranduyloc895/idp-infrastructure.git
git add . && git commit -m "init: Terraform IaC" && git push -u origin main

# Repo 2: GitOps
cd ../idp-gitops
git init && git remote add origin https://github.com/tranduyloc895/idp-gitops.git
git add . && git commit -m "init: GitOps manifests" && git push -u origin main

# Repo 3: Microservices
cd ../idp-microservices
git init && git remote add origin https://github.com/tranduyloc895/idp-microservices.git
git add . && git commit -m "init: Application source" && git push -u origin main
```

---

## Phase 1 — Infrastructure (Terraform + EKS)

### 1.1 Tạo VPC

```bash
cd idp-platform/infrastructure/01-network

# Khởi tạo Terraform
terraform init

# Xem preview
terraform plan

# Apply
terraform apply -auto-approve
```

**Outputs quan trọng:**
```bash
terraform output vpc_id               # → VPC ID
terraform output private_subnets      # → Subnets cho EKS worker nodes
terraform output public_subnets       # → Subnets cho NAT Gateway / EC2
```

**Thời gian:** ~3-5 phút

---

### 1.2 Tạo EKS Cluster + ArgoCD namespace

```bash
cd ../02-cluster-eks

terraform init
terraform plan
terraform apply -auto-approve
```

> ⚠️ **EKS mất ~15-20 phút** để provision cluster + managed node group.

**Sau khi xong, cấu hình kubectl:**

```bash
aws eks update-kubeconfig --name ecommerce-cluster --region us-east-1

# Verify
kubectl get nodes
# NAME                          STATUS   ROLES    AGE   VERSION
# ip-10-0-1-xxx.ec2.internal   Ready    <none>   5m    v1.31.x
```

---

### 1.3 Tạo ECR Repositories

```bash
cd ../03-ecr

terraform init
terraform apply -auto-approve
```

**Tạo 5 ECR repos** cho microservices:
- `retail-store/ui`
- `retail-store/catalog`
- `retail-store/cart`
- `retail-store/checkout`
- `retail-store/orders`

---

### 1.4 Tạo OIDC Provider cho GitHub Actions

```bash
cd ../04-oidc

terraform init
terraform apply -auto-approve
```

**Output:**
```bash
terraform output github_actions_role_arn   # → ARN để dùng trong GitHub Actions secrets
```

**Cấu hình GitHub Secrets** — vào mỗi repo trên GitHub:

1. Truy cập `https://github.com/tranduyloc895/<repo>/settings/secrets/actions`
2. Thêm secret: `AWS_ROLE_ARN` = giá trị `github_actions_role_arn` output ở trên

---

## Phase 2 — GitOps Bootstrap (ArgoCD)

### 2.1 Chạy Bootstrap Script

```bash
cd idp-platform/idp-gitops

# Đảm bảo kubeconfig đúng cluster
kubectl config current-context
# → arn:aws:eks:us-east-1:xxxxxxxxx:cluster/ecommerce-cluster

# Chạy bootstrap
bash scripts/bootstrap.sh
```

**Script sẽ:**
1. ✅ Cài ArgoCD v2.12.0 vào namespace `argocd`
2. ✅ Chờ CRDs + ArgoCD server sẵn sàng
3. ✅ Tạo namespace `monitoring` + Grafana admin secret
4. ✅ Apply `root-application.yml` (App-of-Apps)
5. ✅ In ArgoCD admin password

**📝 LƯU LẠI ArgoCD password!** Script chỉ hiển thị 1 lần.

### 2.2 Truy cập ArgoCD UI

```bash
# Port-forward ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Mở trình duyệt
# https://localhost:8080
# Username: admin
# Password: <từ bước bootstrap>
```

### 2.3 Verify tất cả Applications

```bash
# Xem trạng thái tất cả apps
kubectl get applications -n argocd

# Chờ tất cả sync xong
kubectl get applications -n argocd -w
```

**Kỳ vọng:** Tất cả apps hiển thị `Synced` + `Healthy`:
- `root` — App-of-Apps
- `ui`, `cart`, `catalog`, `checkout`, `orders` — 5 microservices
- `retail-store-databases`, `retail-store-namespace`
- `platform-kps`, `platform-loki`, `platform-promtail` — Monitoring
- `platform-metrics-server`, `platform-cluster-autoscaler`
- `platform-kyverno`, `platform-trivy-operator`, `platform-kube-bench` — Compliance tools
- `compliance-engine` — Compliance API

### 2.4 Verify Monitoring Stack

```bash
# Port-forward Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3001:80

# Mở http://localhost:3001
# Username: admin
# Password: <từ Grafana admin secret>
```

---

## Phase 3 — Backstage IDP Portal (EC2)

### 3.1 Scaffold Backstage Workspace

> ⚠️ **Bước quan trọng!** Hiện tại chưa có `packages/app/` và `packages/backend/`. Cần scaffold trước.

```bash
# Chạy trên máy local (cần Node.js ≥ 20)
cd idp-platform

# Scaffold Backstage workspace tạm
npx @backstage/create-app@latest --path backstage-scaffold

# Merge vào thư mục backstage hiện tại:
# Copy packages/ (cần cho build)
cp -r backstage-scaffold/packages backstage/packages

# Copy workspace config files
cp backstage-scaffold/package.json backstage/package.json
cp backstage-scaffold/yarn.lock backstage/yarn.lock
cp backstage-scaffold/tsconfig.json backstage/tsconfig.json
cp -r backstage-scaffold/.yarn backstage/.yarn
cp backstage-scaffold/.yarnrc.yml backstage/.yarnrc.yml

# Xóa scaffold tạm
rm -rf backstage-scaffold
```

### 3.2 Register Compliance Plugin

```bash
cd backstage

# Thêm plugin dependency vào packages/app/package.json
# Mở packages/app/package.json, thêm vào "dependencies":
#   "@internal/plugin-compliance-scorecard": "link:../../plugins/compliance-scorecard"

# Install dependencies
yarn install
```

**Sửa 3 file theo hướng dẫn trong [`plugins/compliance-scorecard/REGISTRATION.md`](backstage/plugins/compliance-scorecard/REGISTRATION.md):**

**File 1: `packages/app/src/App.tsx`** — Thêm route:
```tsx
import { CompliancePage } from '@internal/plugin-compliance-scorecard';

// Thêm vào <FlatRoutes>:
<Route path="/compliance" element={<CompliancePage />} />
```

**File 2: `packages/app/src/components/catalog/EntityPage.tsx`** — Thêm card:
```tsx
import { EntityComplianceCard } from '@internal/plugin-compliance-scorecard';

// Thêm vào service entity page grid:
<Grid item md={6}>
  <EntityComplianceCard />
</Grid>
```

**File 3: `packages/app/src/components/Root/Root.tsx`** — Thêm sidebar:
```tsx
import SecurityIcon from '@material-ui/icons/Security';

// Thêm vào sidebar:
<SidebarItem icon={SecurityIcon} to="compliance" text="Compliance" />
```

### 3.3 Verify TypeScript Compile

```bash
cd backstage
yarn tsc          # Compile check
yarn build:all    # Full build
```

### 3.4 Provision Backstage EC2

```bash
cd infrastructure/05-backstage-ec2

terraform init
terraform apply -auto-approve
```

**Outputs:**
```bash
terraform output elastic_ip                  # → IP cố định cho Backstage
terraform output instance_id                 # → EC2 instance ID
terraform output github_oauth_callback_url   # → URL cho GitHub OAuth
```

**Thời gian:** ~3-5 phút

### 3.5 Tạo GitHub OAuth App

Xem hướng dẫn chi tiết tại [`backstage/scripts/setup-oauth.md`](backstage/scripts/setup-oauth.md).

**Tóm tắt nhanh:**
1. Truy cập https://github.com/settings/developers → **New OAuth App**
2. Application name: `IDP Portal — Retail Store`
3. Homepage URL: `http://<elastic-ip>:3000`
4. Callback URL: `http://<elastic-ip>:7007/api/auth/github/handler/frame`
5. Click **Register** → Copy **Client ID** + **Client Secret**

### 3.6 Tạo GitHub Personal Access Token

1. Truy cập https://github.com/settings/tokens?type=beta
2. **Generate new token** (Fine-grained)
3. Permissions:
   - Contents: Read & Write
   - Pull requests: Read & Write
   - Workflows: Read & Write
   - Metadata: Read-only
4. Copy token

### 3.7 Deploy Backstage lên EC2

```bash
cd backstage

# Deploy script tự động SSH → clone → build → start
chmod +x scripts/deploy.sh
./scripts/deploy.sh <elastic-ip>
```

**Hoặc deploy thủ công:**

```bash
# SSH vào EC2
ssh ec2-user@<elastic-ip>

# Clone repo
cd /opt/backstage
git clone https://github.com/tranduyloc895/idp-platform.git /tmp/idp-clone
cp -r /tmp/idp-clone/backstage/. .
rm -rf /tmp/idp-clone

# Cấu hình environment
cp .env.example .env
nano .env
# Điền tất cả giá trị:
#   BACKSTAGE_HOST=<elastic-ip>
#   POSTGRES_PASSWORD=<random: openssl rand -base64 32>
#   GITHUB_TOKEN=github_pat_xxx
#   AUTH_GITHUB_CLIENT_ID=Iv1.xxx
#   AUTH_GITHUB_CLIENT_SECRET=xxx
#   ARGOCD_URL=https://<argocd-server>  (hoặc để trống nếu chưa có)
#   ARGOCD_AUTH_TOKEN=xxx               (hoặc để trống)

# Build & Start
docker compose build
docker compose up -d

# Verify
docker compose ps                          # → Tất cả "running"
curl http://localhost:7007/api/health      # → {"status":"ok"}
```

### 3.8 Verify Backstage

1. Mở `http://<elastic-ip>:3000` → Login bằng GitHub
2. Kiểm tra **Software Catalog**: 5 services + 1 System hiển thị
3. Kiểm tra **GitHub Actions tab**: CI runs cho mỗi service
4. Kiểm tra **ArgoCD tab**: Sync status (cần EKS + ArgoCD URL configured)
5. Kiểm tra **Golden Path Template**: Create → "Create a New Microservice"

---

## Phase 4 — Compliance Engine (Local Dev)

### 4.1 Setup Môi trường Python

```bash
cd idp-platform/compliance-engine

# Tạo virtual environment
python -m venv .venv

# Activate
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Cài dependencies
pip install -e ".[dev]"
# Hoặc nếu dùng pyproject.toml:
pip install -r requirements.txt
```

### 4.2 Khởi động bằng Docker Compose (khuyến nghị)

```bash
cd compliance-engine

# Copy env
cp .env.example .env
# Sửa .env nếu cần (mặc định OK cho local dev)

# Khởi động PostgreSQL + Redis + Compliance Engine
docker compose up -d

# Kiểm tra
docker compose ps                               # Tất cả "running"
curl http://localhost:8000/health                # → {"status":"ok"}
curl http://localhost:8000/docs                  # → Swagger UI (OpenAPI)
```

### 4.3 Chạy Database Migration

```bash
cd compliance-engine

# Chạy Alembic migration (tạo tables)
alembic upgrade head
```

### 4.4 Chạy Tests

```bash
cd compliance-engine

# Chạy toàn bộ test suite
pytest tests/ -v

# Với coverage report
pytest tests/ -v --cov=app --cov-report=html

# Chỉ chạy 1 module test
pytest tests/test_scorer/test_engine.py -v
pytest tests/test_recommender/test_rules.py -v
pytest tests/test_api/test_ai_analysis.py -v
```

### 4.5 Test API thủ công

```bash
# Health check
curl http://localhost:8000/health

# Trigger compliance scan (cần kubeconfig valid)
curl -X POST http://localhost:8000/api/v1/scans

# Xem scores
curl http://localhost:8000/api/v1/scores

# Xem findings
curl http://localhost:8000/api/v1/findings

# AI summary (cần GEMINI_API_KEY)
curl http://localhost:8000/api/v1/ai/summary
```

---

## Phase 5 — Compliance Engine (EKS Deploy)

Compliance Engine deploy lên EKS qua ArgoCD (đã có K8s manifests).

### 5.1 Tạo Kubernetes Secrets

```bash
# Tạo namespace (nếu chưa có)
kubectl create namespace compliance --dry-run=client -o yaml | kubectl apply -f -

# Tạo secret cho Compliance Engine
kubectl -n compliance create secret generic compliance-engine-secrets \
  --from-literal=POSTGRES_PASSWORD=<strong-password> \
  --from-literal=GEMINI_API_KEY=<your-gemini-api-key>
```

### 5.2 Build & Push Docker Image

```bash
cd compliance-engine

# Login ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -t compliance-engine:latest .

# Tag
docker tag compliance-engine:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/retail-store/compliance-engine:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/retail-store/compliance-engine:latest
```

### 5.3 Verify ArgoCD Sync

```bash
# ArgoCD sẽ tự detect compliance-engine Application
kubectl get application compliance-engine -n argocd

# Kiểm tra pods
kubectl get pods -n compliance

# Kiểm tra logs
kubectl logs -n compliance deployment/compliance-engine -f
```

---

## Phase 6 — Experiment Workloads

Deploy 3 workloads thử nghiệm với mức tuân thủ khác nhau:

```bash
# Apply experiment manifests
kubectl apply -f idp-gitops/experiments/namespace.yaml

# Workload A — Poor compliance (thiếu security context, resource limits)
kubectl apply -f idp-gitops/experiments/workload-a-poor/

# Workload B — Excellent compliance (đầy đủ security hardening)
kubectl apply -f idp-gitops/experiments/workload-b-excellent/

# Workload C — Fair compliance (có CVE, thiếu readOnlyRootFilesystem)
kubectl apply -f idp-gitops/experiments/workload-c-fair/
```

### Trigger Scan & Xem kết quả

```bash
# Trigger compliance scan
curl -X POST http://localhost:8000/api/v1/scans

# Xem scores (sau vài giây)
curl http://localhost:8000/api/v1/scores | python -m json.tool

# Kỳ vọng:
#   Workload A: ~55-60 (Poor 🔴)
#   Workload B: ~90-95 (Excellent 🟢)
#   Workload C: ~65-70 (Fair 🟡)
```

---

## Phase 7 — GitHub Actions CI Pipeline

### 7.1 Verify CI Workflows

Đã có 5 workflows trong `.github/workflows/`:

| File | Trigger | Service |
|---|---|---|
| `ci-ui.yml` | `push` to `main`, path `src/ui/**` | UI (Java/Spring Boot) |
| `ci-catalog.yml` | `push` to `main`, path `src/catalog/**` | Catalog (Go) |
| `ci-cart.yml` | `push` to `main`, path `src/cart/**` | Cart (Java) |
| `ci-checkout.yml` | `push` to `main`, path `src/checkout/**` | Checkout (NestJS) |
| `ci-orders.yml` | `push` to `main`, path `src/orders/**` | Orders (Java) |

### 7.2 Test E2E Pipeline

```bash
# Sửa 1 file nhỏ trong service UI
cd idp-platform/idp-microservices
echo "// test ci" >> src/ui/src/main/resources/static/assets/js/chat.js

# Commit & push
git add . && git commit -m "test: trigger CI pipeline"
git push origin main

# Kiểm tra GitHub Actions:
# https://github.com/tranduyloc895/idp-microservices/actions
```

**Flow E2E:**
```
Developer push → GitHub Actions CI → Build Docker → Trivy scan → Push ECR → Update GitOps values → ArgoCD sync → Pod deploy on EKS
```

---

## Tear Down

> ⚠️ **QUAN TRỌNG:** Destroy theo thứ tự ngược lại để tránh dependency errors.

```bash
# 1. Xóa Backstage EC2
cd infrastructure/05-backstage-ec2
terraform destroy -auto-approve

# 2. Xóa OIDC
cd ../04-oidc
terraform destroy -auto-approve

# 3. Xóa ECR (⚠️ sẽ xóa tất cả images)
cd ../03-ecr
terraform destroy -auto-approve

# 4. Xóa EKS (⚠️ lâu ~10-15 phút)
cd ../02-cluster-eks
terraform destroy -auto-approve

# 5. Xóa VPC
cd ../01-network
terraform destroy -auto-approve
```

### Chi phí ước tính (dev)

| Resource | Cost/hour |
|---|---|
| EKS Control Plane | ~$0.10/h |
| EC2 t3.medium × 2 (workers) | ~$0.0416/h × 2 |
| EC2 t3.small (Backstage) | ~$0.0208/h |
| NAT Gateway | ~$0.045/h |
| **Tổng** | **~\$0.25/h ≈ \$6/ngày** |

> 💡 **Tip:** `terraform destroy` ngay sau mỗi buổi lab để tiết kiệm. Dùng `terraform apply` lại khi cần.

---

## Troubleshooting

### Infrastructure

| Vấn đề | Giải pháp |
|---|---|
| `terraform init` lỗi S3 backend | Kiểm tra bucket tên đúng + AWS credentials |
| EKS node NotReady | `kubectl describe node <name>` — kiểm tra instance profile / security group |
| `kubectl` không kết nối | `aws eks update-kubeconfig --name ecommerce-cluster --region us-east-1` |

### ArgoCD

| Vấn đề | Giải pháp |
|---|---|
| App `OutOfSync` | ArgoCD UI → Sync → chờ hoặc `argocd app sync <app>` |
| App `Degraded` | `kubectl describe application <app> -n argocd` — xem error message |
| Pod CrashLoopBackOff | `kubectl logs <pod> -n <ns>` — xem logs lỗi |

### Backstage

| Vấn đề | Giải pháp |
|---|---|
| `http://<ip>:3000` không truy cập được | Kiểm tra Security Group port 3000 inbound |
| GitHub login fail | Verify OAuth callback URL khớp Elastic IP |
| Catalog trống | Kiểm tra `GITHUB_TOKEN` có scope `repo` |
| ArgoCD tab trống | Cần `ARGOCD_URL` + `ARGOCD_AUTH_TOKEN` trong `.env` |
| `docker compose build` lỗi | Kiểm tra Node.js version ≥ 20, `yarn install` thành công |
| Plugin không hiển thị | Chạy `yarn install && yarn tsc` lại, kiểm tra REGISTRATION.md |

### Compliance Engine

| Vấn đề | Giải pháp |
|---|---|
| `Connection refused` PostgreSQL | Kiểm tra `docker compose ps` — db phải "running" |
| `GEMINI_API_KEY` invalid | Lấy key mới tại https://aistudio.google.com/app/apikey |
| Scan trả về 0 findings | Cần kubeconfig valid + cluster đang chạy + Kyverno/Trivy installed |
| AI recommendation timeout | Gemini API rate limit — đợi 60s rồi thử lại |

### Logs

```bash
# Backstage logs (trên EC2)
ssh ec2-user@<elastic-ip>
cd /opt/backstage && docker compose logs -f backstage

# Compliance Engine logs (local)
cd compliance-engine && docker compose logs -f compliance-engine

# ArgoCD logs
kubectl logs -n argocd deployment/argocd-server -f

# Kyverno logs
kubectl logs -n kyverno deployment/kyverno -f

# Trivy Operator logs
kubectl logs -n trivy-system deployment/trivy-operator -f
```

---

## Tổng hợp Services & Ports

| Service | Port (Local) | Port (EKS) | URL |
|---|---|---|---|
| Backstage UI | 3000 | 3000 | `http://<elastic-ip>:3000` |
| Backstage API | 7007 | 7007 | `http://<elastic-ip>:7007/api/health` |
| ArgoCD UI | 8080 (port-forward) | 443 | `https://localhost:8080` |
| Grafana | 3001 (port-forward) | 80 | `http://localhost:3001` |
| Compliance Engine | 8000 | 8000 | `http://localhost:8000/docs` |
| PostgreSQL (Backstage) | 5432 | 5432 | — |
| PostgreSQL (Compliance) | 5433 | 5432 | — |
| Redis | 6379 | 6379 | — |

---

## Cấu trúc Repository

```
idp-platform/
├── infrastructure/              # Terraform IaC
│   ├── 01-network/              #   VPC, subnets, NAT Gateway
│   ├── 02-cluster-eks/          #   EKS cluster, node group, IRSA
│   ├── 03-ecr/                  #   ECR repositories
│   ├── 04-oidc/                 #   GitHub Actions OIDC provider
│   └── 05-backstage-ec2/       #   EC2 cho Backstage portal
├── idp-gitops/                  # GitOps — ArgoCD source of truth
│   ├── argocd/                  #   App-of-Apps definitions
│   ├── apps/                    #   Per-service Helm values
│   ├── charts/microservice/     #   Shared Helm chart
│   ├── platform/                #   Add-ons (monitoring, kyverno, trivy, kube-bench)
│   ├── compliance/              #   Compliance Engine K8s manifests
│   ├── experiments/             #   Test workloads (Poor/Excellent/Fair)
│   └── scripts/                 #   Bootstrap scripts
├── idp-microservices/           # Application source code
│   ├── .github/workflows/       #   5 GitHub Actions CI pipelines
│   └── src/                     #   ui, cart, catalog, checkout, orders
├── backstage/                   # Backstage IDP Portal
│   ├── catalog/                 #   Software Catalog entities
│   ├── templates/               #   Golden Path Template
│   ├── plugins/                 #   Compliance Scorecard plugin
│   └── scripts/                 #   Deploy + OAuth setup
├── compliance-engine/           # Python/FastAPI Compliance Scorecard
│   ├── app/                     #   Models, collectors, scorer, recommender, API
│   ├── tests/                   #   Unit + integration tests
│   ├── fixtures/                #   Sample data for testing
│   └── alembic/                 #   Database migrations
└── docs/                        # Architecture docs (TBD)
```
