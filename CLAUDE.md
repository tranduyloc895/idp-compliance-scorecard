# CLAUDE.md — IDP Compliance Scorecard

Khóa luận: Internal Developer Platform tối giản trên Amazon EKS theo GitOps, tích hợp Continuous Compliance Scorecard và khuyến nghị khắc phục bằng AI cho Kubernetes workloads. Monorepo; remote `tranduyloc895/idp-compliance-scorecard`, nhánh chính `main`.

## Trạng thái dự án — đọc trước khi làm

- Hệ thống **chưa từng được triển khai thử**. Dấu ✅, tên workload Poor/Fair/Excellent và các khoảng điểm trong README/SETUP là kỳ vọng, không phải kết quả đo.
- `docs/SETUP.md` **chưa khớp** với code và không dùng nguyên trạng làm runbook được. Danh sách lệch (đánh số #1–#27) và các lỗi ảnh hưởng kết quả khóa luận nằm trong `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`.
- Khi sửa một vấn đề có trong audit, ghi rõ mã số (ví dụ "Sửa vấn đề #13 từ audit"). Không sửa file audit trừ khi được yêu cầu rõ ràng.
- Thứ tự ưu tiên đã chốt trong audit (mục 7): chứng minh luồng cốt lõi và dữ liệu điểm đáng tin trước, rồi mới mở rộng AI.

## Cấu trúc repo

```
infrastructure/      Terraform root modules: 01-network, 02-cluster-eks (EKS/IRSA/Argo CD), 03-ecr, 04-oidc, 05-backstage-ec2
idp-gitops/          Argo CD App-of-Apps (argocd/), Helm values theo service (apps/), shared chart (charts/microservice),
                     platform add-ons (monitoring, kyverno + 8 policies, trivy-operator, kube-bench, autoscaler),
                     compliance/ (deploy engine + Redis), experiments/ (workload A/B/C)
idp-microservices/   Retail Store: ui/cart/orders (Java 21, Spring), catalog (Go), checkout (NestJS); CI ở idp-microservices/.github/workflows
compliance-engine/   Python 3.12 / FastAPI: collector → normalizer → scorer → recommender (rule-based + Gemini); SQLAlchemy/asyncpg, Redis
backstage/           Config, catalog, plugin compliance-scorecard (React), Golden Path template; chưa có packages/app, packages/backend
docs/                Tài liệu dự án: SETUP.md, audit, hướng dẫn graphify (GRAPHIFY.md)
context/             Nhật ký thay đổi do AI ghi (xem bên dưới)
graphify-out/        Knowledge graph của repo (bị git ignore, xem mục graphify)
```

Luồng dự kiến: push → CI build/Trivy/push ECR → commit image tag vào GitOps → Argo CD deploy lên EKS → Kyverno/Trivy/kube-bench tạo report → `POST /api/v1/scans` thu thập, chuẩn hóa, chấm điểm → PostgreSQL + Redis → Backstage plugin hiển thị → khuyến nghị rule hoặc Gemini.

Scoring: 4 miền (Cluster Security 35%, Workload Security 35%, Supply Chain 20%, Platform Config 10%); Excellent ≥90, Good ≥75, Fair ≥60, Poor <60.

## Lệnh thường dùng

Compliance engine (chạy trong `compliance-engine/`):

```bash
python -m pytest tests/ -q
```

- Cần Python ≥3.12. `pip install -e ".[dev]"` hiện **lỗi** do `build-backend = "setuptools.backends.legacy:build"` (audit #13); đến khi sửa, cài dependencies trực tiếp từ `pyproject.toml` vào venv.
- `tests/test_scorer/test_engine.py` đang có lỗi cú pháp làm pytest dừng ở collection.

## Quy tắc làm việc

- Code viết bằng tiếng Anh; comment, tài liệu và context log có thể dùng tiếng Việt.
- **Không chạy** `terraform apply/destroy`, `kubectl apply/delete` lên cluster thật, hay push image lên ECR khi chưa được yêu cầu rõ ràng. `*.tfstate` bị git ignore; trong git worktree có thể không có state và `.terraform/`.
- Không commit secret. Các file `secret.yaml` trong `idp-gitops` chứa placeholder (`CHANGE_ME_BASE64`), không phải dữ liệu thật.
- Contract API giữa `compliance-engine/app/api/routes/` và `backstage/plugins/compliance-scorecard/src/api/` hiện **lệch nhau** (audit mục 5.1). Khi sửa một bên, kiểm tra bên còn lại.
- Collector lỗi hoặc không có dữ liệu đang cho ra 100 điểm (audit mục 5.2). Đừng coi điểm cao là bằng chứng hệ thống chạy đúng.
- Giữ nguyên cấu trúc thư mục trừ khi có lý do rõ ràng và ghi lại trong context log.

## Nhật ký thay đổi (`context/`)

Sau mỗi thay đổi code, cấu hình, tài liệu hoặc thực nghiệm, tạo hoặc cập nhật `context/YYYY-MM-DD_<tên-ngắn-gọn>.md` (cùng quy ước với `GEMINI.md`):

```markdown
# <Tiêu đề mô tả thay đổi>

**Ngày:** YYYY-MM-DD
**Thành phần:** <infrastructure | compliance-engine | backstage | gitops | microservices | docs | other>
**Loại:** <fix | feature | refactor | config | docs | test | experiment>

## Mô tả
## Các file đã thay đổi
## Ghi chú / Vấn đề còn lại
```

Ghi sau khi hoàn thành thay đổi. Không xóa log cũ. Trước khi sửa một thành phần, đọc các log liên quan trong `context/`.

## Tài liệu tham khảo

- `docs/SETUP.md`: runbook setup 7 phase (đọc kèm audit).
- `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`: mục tiêu khóa luận, bản đồ triển khai, danh sách lệch, thứ tự xử lý.
- `docs/GRAPHIFY.md`: cách dùng knowledge graph để nắm context và lên plan.
- `docs/DeCuongKLTN_23520868_TranDuyLoc.pdf`: đề cương (chỉ có trên máy local, bị git ignore).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
