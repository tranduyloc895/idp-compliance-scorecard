# Context dự án và đối chiếu SETUP.md

Ngày rà soát: 02/11/2026. Baseline: commit `fdf85aa`.

## 1. Kết luận hiện tại

Dự án có mã nguồn cho phần lớn các khối kiến trúc trong đề cương, nhưng chưa đủ điều kiện coi là hệ thống đã tích hợp và triển khai thành công. `SETUP.md` chưa khớp với repository và không thể dùng nguyên trạng làm runbook từ đầu đến cuối.

Theo thông tin chủ dự án cung cấp, chưa triển khai thử. Các dấu ✅ trong README, tên workload Poor/Fair/Excellent và các khoảng điểm dự kiến không phải bằng chứng chạy thực tế.

Phạm vi rà soát: đề cương PDF 10 trang (gồm hình kiến trúc), cấu trúc repository, Terraform, GitOps/Helm/manifests, CI, Dockerfiles, cấu hình và luồng dịch vụ Retail Store, Backstage/plugin/template, các module Compliance Engine và bộ test. Đây là rà soát kiến trúc, tích hợp và khả năng làm theo setup; không phải chứng nhận mọi dòng nghiệp vụ Retail Store đã đúng hay kiểm thử E2E trên AWS.

## 2. Mục tiêu khóa luận

Nguồn: `docs/DeCuongKLTN_23520868_TranDuyLoc.pdf`.

- Thời gian đề cương: 01/09/2026–20/12/2026.
- IDP tối giản theo PE-RM: Backstage, GitHub Actions → ECR → Argo CD, EKS, Terraform.
- Ít nhất 5 microservices: UI, Catalog, Cart, Orders, Checkout.
- Đóng góp chính: Collector → Normalizer → Scorer → Recommender và dashboard tuân thủ.
- Ba nguồn dữ liệu: Kyverno PolicyReport, Trivy VulnerabilityReport, kube-bench JSON.
- Trọng số: Cluster Security 35%, Workload Security 35%, Supply Chain 20%, Platform Config 10%.
- Phân loại: Excellent ≥90, Good ≥75, Fair ≥60, Poor <60.
- Ít nhất 20 loại vi phạm được rule-based recommender bao phủ; so sánh với Gemini bằng accuracy, applicability, specificity, latency và chi phí API.
- Thực nghiệm 3+ workload đối chứng và chu trình sửa lỗi → scan lại → điểm cải thiện.
- Các chỉ tiêu điểm và tỷ lệ AI áp dụng được ≥80% là mục tiêu cần đo, chưa phải kết quả.

## 3. Bản đồ triển khai hiện có

| Thành phần | Đã có trong repository | Trạng thái cần hiểu đúng |
|---|---|---|
| `infrastructure/` | 5 root module: VPC, EKS/IRSA/Argo CD, ECR, GitHub OIDC, EC2 Backstage | Chưa xác minh apply; backend/inputs/bootstrap chưa thống nhất |
| `idp-microservices/` | Java 21 UI/Cart/Orders, Go Catalog, NestJS Checkout; Dockerfiles; 5 workflow CI | Có nền ứng dụng Retail Store và mã mang copyright Amazon; cần phân biệt nguồn kế thừa với phần tự phát triển khi viết luận văn |
| Datastore ứng dụng | Catalog MySQL/MariaDB, Cart DynamoDB Local, Orders PostgreSQL, Checkout Redis | Khác database dành cho Compliance Engine |
| `idp-gitops/` | App-of-Apps, shared Helm chart, DB/PVC, monitoring, autoscaler, 8 Kyverno policies Audit, Trivy, kube-bench, compliance API/Redis | Trộn đường dẫn repo tách riêng và monorepo; còn placeholder |
| `compliance-engine/` | FastAPI, SQLAlchemy/asyncpg, Redis; collectors, normalizer, scorer, rules, Gemini; fixtures/tests | Có logic thực, còn lỗi build, test, migration và semantics dữ liệu |
| `backstage/` | Config, catalog 5 services + System, plugin React, template, Docker/deploy scripts | Chưa có workspace `packages/app`, `packages/backend`, root package.json/yarn.lock |
| Thực nghiệm | A/B/C trong cùng namespace `compliance-test` | Chưa có kết quả đo; API hiện chỉ chấm theo lần scan/namespace |

Luồng dự kiến: developer push → CI build/scan/push image → commit image tag vào GitOps → Argo CD deploy → scanners tạo báo cáo → scan API thu thập/chuẩn hóa/tính điểm → PostgreSQL + Redis → Backstage proxy/plugin → khuyến nghị rule hoặc Gemini.

Scoring hiện thực: mỗi miền lấy `passed / total * 100`, trừ 15 cho mỗi Critical FAIL và 5 cho mỗi High FAIL, tổng penalty mỗi miền tối đa 50, clamp 0–100, sau đó cộng theo trọng số. Miền không có finding hiện nhận 100 điểm.

## 4. Những điểm SETUP.md chưa khớp

### A. Repository, Terraform, CI và bootstrap

1. **Mô hình repository chưa thống nhất.** Git remote local là `tranduyloc895/idp-compliance-scorecard`; setup dùng thư mục/repo `idp-platform`, hướng dẫn tách 3 repo; script Backstage lại clone `idp-platform.git`. Workflows nằm dưới `idp-microservices/.github/workflows`, không nằm ở `.github/workflows` root của repository hiện tại. Cần chọn rõ monorepo hay tách repo và sửa đồng bộ path, trigger, build context, OIDC trust và Argo CD source.
2. **Thiếu S3 backend bucket thứ hai.** Setup chỉ tạo `devsecops-tfstate-23520868-23521463`; module 04/05 dùng `idp-platform-tfstate-tranduyloc895`. ECR còn dùng state key `05-ecr/terraform.tfstate` dù thư mục là 03; tên key không tự gây lỗi nhưng phải ghi đúng khi vận hành state.
3. **Tên Terraform output sai.** Network xuất `private_subnet_ids`, `public_subnet_ids`; setup gọi `private_subnets`, `public_subnets`. OIDC xuất `role_arn`; setup gọi `github_actions_role_arn`.
4. **Thiếu input bắt buộc.** Module 04 cần `ecr_account_id`; module 05 cần `vpc_id`, `subnet_id`. SSH deploy cần key pair/cách xác thực phù hợp, trong khi `key_name` mặc định rỗng. Nhánh SSM của deploy script chỉ in chỉ dẫn và còn trỏ đến `scripts/deploy-local.sh` không có trong repo.
5. **Argo CD bị cài bởi hai cơ chế.** Terraform có `helm_release.argocd`; bootstrap lại apply upstream manifests v2.12.0. Cần một cơ chế sở hữu/cài đặt trước khi dùng runbook.
6. **Bootstrap Bash có rủi ro dừng ở bước sinh mật khẩu.** `set -euo pipefail` kết hợp `tr ... | head -c 24` có thể làm pipeline thất bại do SIGPIPE. Cần kiểm tra/sửa trước lần bootstrap đầu.
7. **Argo CD sources còn placeholder.** Compliance Engine, kube-bench, Kyverno/policies, Trivy tham chiếu `YOUR_ORG/idp-platform`; path có prefix `idp-gitops/`, khác các app còn lại dùng repo `idp-gitops` với path tương đối ở root. Không thể kỳ vọng tất cả Synced/Healthy ngay sau Phase 2.
8. **Autoscaler sai region so với Terraform.** `platform/cluster-autoscaler/values.yaml` dùng `ap-southeast-1`; Terraform dùng `us-east-1`. Role ARN, image registry/account và các image tag đang hardcode cần khớp account/image thực.
9. **Chưa có image bootstrap.** Phase 2 chạy trước build/push image của Compliance Engine và các microservices. ECR chỉ khai báo 5 repo ứng dụng, chưa khai báo `retail-store/compliance-engine` mà Phase 5 push vào.
10. **Thiếu GitHub secret cho cập nhật GitOps.** 5 workflow đọc `GITOPS_PAT` ngoài `AWS_ROLE_ARN`. Token Backstage trong `.env` không tự trở thành secret của workflow. Workflow template service mới lại dùng `GITOPS_TOKEN` và hardcode tên IAM role khác module Terraform.
11. **Tên Application cần sửa trong phần kỳ vọng.** Các service có tên `retail-store-ui`, `retail-store-cart`, ...; monitoring stack là `platform-kube-prometheus-stack`. Không phải `ui`, `cart`, `platform-kps` như setup liệt kê. Helm release monitoring là `kps`; cần lấy tên Service Grafana thực tế thay vì giả định `kube-prometheus-stack-grafana`.
12. **Bảng chi phí không đại diện cấu hình.** Setup tính 2 worker `t3.medium`; Terraform mặc định 3 worker `t3.large`, min 2/max 4. Không sử dụng tổng tiền trong setup để dự toán; chưa kiểm tra giá AWS hiện hành trong đợt audit này.

### B. Compliance Engine local và EKS

13. **Python và lệnh cài đặt sai.** Setup ghi Python ≥3.11; `pyproject.toml` đòi ≥3.12. Không có `requirements.txt`. Build backend đang là `setuptools.backends.legacy:build`; thử `pip install -e "./compliance-engine[dev]"` trong Python 3.12 thất bại với `Cannot import 'setuptools.backends.legacy'`. Dockerfile cũng sử dụng `pip install .` nên cùng cấu hình build lỗi.
14. **Migration chưa thể dùng như hướng dẫn.** Migration gốc duy nhất chỉ tạo `ai_summaries`, tham chiếu `scans` chưa được migration nào tạo. `scan_id` vừa có `index=True`, vừa tạo explicit index trùng tên. Startup API đang gọi `Base.metadata.create_all`, không chạy Alembic như docstring nói; chạy Alembic sau startup có nguy cơ trùng table. Cần thống nhất một quy trình schema từ DB trắng.
15. **POST scan thiếu request body.** API yêu cầu `ScanRequest`; lệnh trong Phase 4/6 không gửi JSON. Cần gửi `Content-Type: application/json`, body `{}` hoặc `{"namespace":"compliance-test"}`, rồi poll `/api/v1/scans/{id}` tới completed/failed. CronJob đã gửi `{}` đúng.
16. **Kubeconfig Compose không đủ cho EKS.** Compose mount vào `/root/.kube/config` trong khi image chạy user 1000; Dockerfile không cài AWS CLI để thực thi EKS exec credential. Cần giải quyết quyền đọc và cơ chế cấp token, hoặc chạy API local ngoài container với kubeconfig/AWS CLI phù hợp.
17. **Secret tạo sai key.** Setup tạo `POSTGRES_PASSWORD`, `GEMINI_API_KEY`; Deployment đọc `postgres-user`, `postgres-password`, `gemini-api-key`. File GitOps `secret.yaml` còn `CHANGE_ME_BASE64` không phải dữ liệu base64 hợp lệ. Cần chọn cách quản lý secret và tránh để Argo CD đồng bộ manifest placeholder đè lên secret tạo thủ công.
18. **Database EKS không tồn tại trong thiết kế hiện có.** Deployment trỏ `postgresql.backstage.svc.cluster.local`, nhưng Backstage PostgreSQL nằm trong Docker Compose trên EC2 và bind host `127.0.0.1:5432`. Không có Service PostgreSQL namespace backstage hay manifest tạo user/database compliance tương ứng. Redis có, PostgreSQL cho engine trên EKS chưa có.
19. **Image EKS chưa được thay.** Manifest dùng `YOUR_ECR_REGISTRY/compliance-engine:latest`; setup push `.../retail-store/compliance-engine:latest` nhưng không có bước cập nhật Deployment.
20. **Thiếu đường truy cập API EKS.** Service engine là ClusterIP. Trước các curl `localhost:8000` ở Phase 6 cần port-forward hoặc đường truy cập đã cấu hình; nếu API local vẫn chạy, có thể đang gọi nhầm instance.
21. **Lịch local chưa được cài.** `SCAN_INTERVAL_SECONDS` có trong settings nhưng không có background scheduler sử dụng. Scan định kỳ hiện do Kubernetes CronJob gọi API mỗi 30 phút, không tự chạy khi mở Compose.

**Lỗi chặn scan trên EKS đã tái hiện ở mức hàm:** `app/main.py:93` gọi `await config.load_incluster_config()`. Trong `kubernetes-asyncio 36.1.0` được resolve theo pyproject, đây là hàm đồng bộ. Mock phần load config thành công vẫn làm init thất bại với `object NoneType can't be used in 'await' expression`; exception bị bắt và trả client `None`. Phải sửa trước khi kiểm thử scan trong Pod.

### C. Backstage và Golden Path

22. **Cần scaffold thật và hoàn thiện build.** Setup đã thừa nhận thiếu workspace, nhưng chưa chứng minh scaffold `@latest` tương thích plugin/config/Dockerfile. Dockerfile chạy `yarn install --immutable` trước khi copy các package manifest của workspace; cần kiểm chứng cấu trúc output backend thay vì giả định có `dist/index.js`.
23. **Port và URL đăng nhập lệch.** Compose chỉ publish `3000:7007`, trong khi backend.baseUrl, OAuth callback, Terraform output và deploy health check dùng host port 7007. Cần thống nhất URL public/backend/callback và mappings.
24. **Chưa có kết nối EC2 → Compliance Engine.** Proxy target `http://compliance-engine:8000` không có service tương ứng trong Compose Backstage và không phải hostname mà EC2 tự resolve thành Kubernetes ClusterIP. Argo CD cũng cần endpoint EC2 truy cập được; localhost port-forward trên máy developer không phải endpoint EC2.
25. **Catalog annotation không khớp Argo CD Application.** Ví dụ `argocd/app-name: ui` trong khi Application là `retail-store-ui`. Catalog cũng chưa khai báo Group `platform-team`/User; cấu hình GitHub OAuth chưa thể hiện đầy đủ sign-in resolver.
26. **Template chưa được đăng ký.** Catalog entrypoint chỉ liệt kê System + 5 Component, không có location tới `templates/new-microservice/template.yaml`. Không thể mặc định template xuất hiện ở Create.
27. **Golden Path chưa tạo service chạy được.** Skeleton chỉ có README, Dockerfile, catalog-info và CI, chưa có source/pom.xml/go.mod/package.json tương ứng; không có bước sinh Helm values/Argo CD Application riêng cho GitOps PR. Nội dung mô tả PR không tự tạo các file đó. ECR/OIDC và secret của repo mới vẫn cần xử lý.

## 5. Các lỗi ảnh hưởng trực tiếp kết quả khóa luận

### 5.1 API và frontend không cùng contract

Nguồn: `compliance-engine/app/api/routes/` và `backstage/plugins/compliance-scorecard/src/api/`.

| Luồng | Backend thực trả/nhận | Frontend đang kỳ vọng |
|---|---|---|
| Findings | `{cached, data: {findings, total, limit, offset}}`; resource fields phẳng | `{items, total, scan_id}`; `resource` object |
| History | `{history, count}` | Mảng `ScoresResponse[]` trực tiếp |
| Recommendation URL | DB ID dạng integer | `finding_id` dạng `KYV-...`/`TRV-...` |
| Rule recommendation | `rule_id`, `title`, `fix_description`, `yaml_fix` | `policy`, `fix`, `severity` |
| AI recommendation | `strategy` ở route đơn | `strategy_used` |
| Compare | `{recommendations: {rule_based, ai_basic, ai_context_enriched}}` | `{basic, context_enriched}` |

Client chỉ ép kiểu TypeScript, không chuyển đổi response. Findings có thể hiển thị rỗng, history không vẽ được và recommendation trả 422. Entity card hiện gọi score chung, chưa map entity sang workload. Dashboard còn thiếu empty state cho DB chưa có scan: GET scores 404 đưa trang vào lỗi trước khi nút Scan Now xuất hiện.

### 5.2 Không có dữ liệu đang bị hiểu thành tuân thủ hoàn hảo

Collector bắt nhiều lỗi và trả list rỗng; aggregator tiếp tục dù source lỗi. Scorer cho miền rỗng 100 điểm. Vì vậy mất quyền đọc CRD, thiếu report hoặc scanner lỗi có thể tạo scan completed với điểm Excellent. Test hiện còn xác nhận `[] → 100`. Cần trạng thái missing/error/stale, coverage và tiêu chí scan hợp lệ trước khi dùng điểm để chứng minh thực nghiệm.

### 5.3 Đơn vị chấm điểm chưa đáp ứng so sánh A/B/C

Ba workload đều ở `compliance-test`; mỗi lần scan chỉ persist một ScoreRecord theo namespace được yêu cầu, không chấm riêng từng workload. Scan không filter namespace tạo score chung toàn cluster. Entity card cũng đọc chung score. Không thể gọi `/scores` rồi nhận ba điểm A/B/C như setup mô tả.

Ngoài ra GET `/scores` không lọc `namespace IS NULL`, nên scan riêng namespace gần nhất có thể bị trả như điểm cluster-wide. kube-bench và ClusterPolicyReport vẫn được đưa vào scan namespace; cần định nghĩa rõ cách tách điểm hạ tầng và điểm workload.

### 5.4 Recommender và phép đo chưa đủ mục tiêu

- `RULES` thực tế có **15 rules**, không phải 25 như comment, chưa đạt tối thiểu 20 trong đề cương.
- Rule cho anonymous-auth/kubelet/service account đang tái sử dụng `security-context-full.yaml`; đây không phải bản vá đặc thù cho mọi control được mô tả.
- Templates còn placeholder resource/container/image, chưa render theo workload. Cần đo applicability bằng kiểm tra/apply thực tế, không suy ra từ việc có chuỗi YAML.
- Finding ORM không persist `raw_metadata`; không giữ đầy đủ context gốc cho lần đọc lại. AI prompt hiện bổ sung tài liệu tĩnh, chưa đọc manifest workload thực tế.
- Có đo latency; chưa thấy ghi nhận token usage/cost và bộ dữ liệu/rubric đánh giá accuracy/applicability/specificity. `RecommendationRecord` có model nhưng route recommendation chưa persist kết quả vào nó.
- AI summary cache dùng key `latest`, chưa invalidate cùng scan mới. Health endpoint còn gọi Gemini generation thật khi có key, làm lẫn traffic probe với traffic thực nghiệm.
- Cần kiểm chứng nguồn/version các CIS references; ngay trong code, cùng số 5.4.1 được diễn giải khác nhau giữa prompt và rule. Audit này chưa xác minh tài liệu khoa học/benchmark bên ngoài.

### 5.5 Các điểm cần xác minh khi triển khai scanner/workload

- kube-bench CronJob gọi `kubectl` trong image kube-bench nhưng repo chưa có bước đảm bảo binary này tồn tại; cần kiểm tra image. ConfigMap results `{}` do Argo CD selfHeal quản lý có thể bị khôi phục sau khi CronJob ghi dữ liệu.
- kube-bench parser gọi `.get()` trước khi kiểm tra `isinstance(data, list)`, nên nhánh hỗ trợ JSON list không hoạt động.
- Trivy dedup key thiếu namespace/package; finding ID thiếu container/package. Có thể mất hoặc gộp nhầm CVE giữa tài nguyên/gói.
- Workload B khai báo probe/containerPort 8080 với image nginx thường nhưng chưa có cấu hình nginx listen 8080; `containerPort` không đổi cổng ứng dụng. B/C chạy UID 1000 cần kiểm tra đường dẫn nginx ghi dữ liệu/PID. Phải kiểm tra Pod Ready trước khi gọi đây là workload đối chứng hoạt động.
- Chưa có Kyverno policy kiểm tra NetworkPolicy trong bộ 8 policies; việc B có NetworkPolicy không tự đảm bảo scorer phân biệt được đặc tính này.
- Chart microservice chưa render securityContext để áp dụng đầy đủ các hardening fixes thông qua values.

## 6. Kiểm chứng trong đợt rà soát

- Dùng Python 3.12 trong venv tạm ngoài repository; không sửa source để vượt lỗi build.
- Lệnh cài package theo setup thất bại ở build backend, trước khi cài ứng dụng.
- Parse 52 file Python (đọc UTF-8 có hỗ trợ BOM), phát hiện một lỗi cú pháp list comprehension tại `tests/test_scorer/test_engine.py:147`.
- Cài trực tiếp danh sách dependencies/dev từ pyproject vào venv audit để tách lỗi packaging khỏi lỗi source; không có lockfile nên kết quả gắn với phiên bản được resolve ở lần audit này. Python 3.12.14, pytest 9.2.0, FastAPI 0.162.0, Pydantic 2.14.2, SQLAlchemy 2.1.6, kubernetes-asyncio 36.1.0.
- `python -m pytest tests/ -q --disable-warnings -p no:cacheprovider`: **dừng ở collection, 1 SyntaxError**, chưa chạy suite hoàn chỉnh.
- Chạy chẩn đoán với `--ignore=tests/test_scorer/test_engine.py`: **45 passed, 1 failed**. Test fail là `test_normalize_all_returns_only_valid`: tạo `RawFinding(source="unknown_source")` bị Pydantic từ chối trước khi gọi normalizer. Đây là lỗi thiết kế test, không chứng minh normalizer đã xử lý sai một input hợp lệ.
- Kiểm chứng trực tiếp: `len(RULES) == 15`; scorer với input rỗng trả `100.0`; in-cluster init trả None sau khi await nhầm hàm đồng bộ (mock việc load config, không gọi Kubernetes thật).
- Không có `docker`, `terraform`, `kubectl`, `helm` trong PATH của session này. Chưa chạy Docker build/Compose, Terraform validate/plan/apply, Helm render hay thử AWS/Gemini/E2E. Không kết luận từ unit test rằng deployment đã chạy được.
- Không chỉnh `SETUP.md` hay mã triển khai trong đợt audit; file này lưu context và danh sách lệch để tránh viết lại hướng dẫn theo một kiến trúc chưa được chốt.

## 7. Thứ tự xử lý để đi tới lần thực nghiệm đầu

1. Chốt mô hình repo, vị trí PostgreSQL compliance và đường kết nối Backstage EC2 ↔ EKS; thống nhất Argo CD chỉ có một cơ chế cài.
2. Sửa packaging, cú pháp test, migration từ DB trắng và K8s client init; chạy engine local + DB/Redis, kiểm tra scan fixtures và API contract.
3. Sửa missing-data semantics và đơn vị score workload/namespace; kiểm thử lỗi scanner và phân biệt ba workload.
4. Scaffold/pin Backstage workspace; nối API contract; hoàn thiện catalog/auth/proxy và Golden Path cho ít nhất một ngôn ngữ trước.
5. Hoàn thiện Terraform inputs/backend, GitOps paths/secrets/images/region; build/push image trước bootstrap apps; kiểm tra scanner reports có dữ liệu thật.
6. Chạy E2E nhỏ: một workload → scan → finding → rule/AI → sửa qua GitOps → scan lại. Lưu evidence, versions, image digest, scan ID và timestamp.
7. Mở rộng A/B/C, đủ rule coverage, rubric chấm chất lượng AI, token/cost/latency và các lần lặp thực nghiệm; cập nhật SETUP.md từ các lệnh đã được xác minh.

Ưu tiên chứng minh luồng cốt lõi hoạt động và dữ liệu điểm đáng tin trước khi mở rộng AI summary/remediation roadmap.
