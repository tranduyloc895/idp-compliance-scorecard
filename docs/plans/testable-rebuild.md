Mục tiêu: đưa dự án IDP Compliance Scorecard từ trạng thái "mới gen code, chưa chạy lần nào" sang trạng thái kiểm thử được và dựng lại nhanh trên AWS. Bắt tối đa lỗi bằng kiểm tra tĩnh và CI trước khi tốn tiền AWS; mỗi buổi lab chỉ dựng và huỷ phần tốn tiền, mỗi chiều bằng một lệnh.

## Theo dõi tiến độ (bắt buộc, làm trước tiên)
- Việc đầu tiên: tạo branch `feat/testable-rebuild` từ main, lưu nguyên văn prompt này vào docs/plans/testable-rebuild.md rồi commit.
- Tạo context/YYYY-MM-DD_testable-rebuild-progress.md. File này chứa: checklist mọi mục của các giai đoạn (- [ ] / - [x]), mục đang làm, các quyết định đã chốt kèm lý do, lỗi đang dở. Cập nhật file và commit sau MỖI mục nhỏ hoàn thành, không đợi hết giai đoạn.
- Commit nhỏ và thường xuyên, message ghi mã audit nếu có. Không để thay đổi lớn ở trạng thái chưa commit.
- Khi phải dừng (hết lượt, hoặc chờ tôi xác nhận): ghi "Bước tiếp theo: ..." vào progress file trước khi kết thúc.
- Khi được yêu cầu "tiếp tục": đọc progress file mới nhất, xem `git log --oneline main..HEAD` và `git status`, rồi làm tiếp từ "Bước tiếp theo". Không làm lại các mục đã [x].

## Bối cảnh — đọc trước khi làm
- Đọc CLAUDE.md, docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md (audit, các vấn đề đánh số #1–#27 và mục 5.x), docs/SETUP.md, docs/GRAPHIFY.md và các log trong context/.
- Dùng graphify (`graphify query/path/explain/affected`) để nắm luồng trước khi grep.
- Sau mỗi giai đoạn: ghi context log theo quy ước trong CLAUDE.md và chạy `graphify update .`.
- Không push và không merge vào main khi chưa hỏi tôi.

## Môi trường và ràng buộc
- Máy local Windows, 16GB RAM. KHÔNG chạy cluster, docker compose hay build image trên máy. Trên máy chỉ sửa code và chạy lệnh nhẹ: `terraform fmt`, `terraform init -backend=false` + `validate`, `tflint`, `pytest` của compliance-engine, `tsc`.
- Tool cài trong C:\tools (vd C:\tools\terraform, C:\tools\docker), thêm vào PATH khi cần. Được phép đề xuất cài: terraform, tflint, docker CLI, python 3.12, node và các CLI tĩnh khác. Đầu phiên, kiểm tra tool nào đã có; thiếu thì liệt kê và hỏi tôi trước khi cài.
- KHÔNG cài kubectl, helm, kind/k3d lên máy. Mọi bước cần helm/kubeconform/kyverno CLI chạy trong GitHub Actions. Trên EKS, script dùng kubectl/helm qua Docker image hoặc AWS CloudShell.
- Việc nặng chạy trong GitHub Actions: docker build 6 image, helm/kubeconform/kyverno, smoke test compliance engine bằng docker compose.
- Việc cần Kubernetes chạy trên EKS, chỉ sau khi tôi đồng ý chạy `aws-up`.
- KHÔNG chạy `terraform apply/destroy`, không tạo tài nguyên AWS, không push image và không push git khi tôi chưa xác nhận rõ ràng. `terraform plan` chỉ chạy khi tôi đồng ý dùng credential AWS.
- Không commit secret thật. Mọi giá trị thật đi qua SSM Parameter Store hoặc `.env` bị git ignore.
- Kiểm tra được bằng lệnh nhẹ trên máy, trong CI hoặc trên AWS thì phải kiểm tra thật, không chỉ "đọc thấy hợp lý". Mục nào chưa kiểm được thì ghi "chưa kiểm chứng", kèm lỗi dự kiến có thể gặp và cách kiểm tra.

## Quyết định đã chốt
1. Monorepo: repo duy nhất là github.com/tranduyloc895/idp-compliance-scorecard. Mọi Argo CD Application trỏ về repo này, path bắt đầu bằng `idp-gitops/...`. Bỏ mọi tham chiếu tới `YOUR_ORG/idp-platform` và tới repo riêng `tranduyloc895/idp-gitops.git`. CI chuyển về `.github/workflows` tại root repo, dùng path filter cho từng service.
2. Chia hạ tầng thành 2 lớp:
   - Lớp nền, tạo một lần, KHÔNG destroy sau mỗi buổi lab (chi phí gần 0): S3 state bucket (một bucket duy nhất, `use_lockfile`), ECR (5 service + `compliance-engine`, `force_delete = false`, lifecycle policy giữ N image gần nhất), GitHub OIDC provider + IAM role cho CI, SSM Parameter Store chứa secret.
   - Lớp tạo-huỷ mỗi buổi lab: VPC/NAT (`single_nat_gateway = true`), EKS + node group, Argo CD, Backstage EC2.
3. Argo CD chỉ được cài bằng MỘT cơ chế: Terraform `helm_release` trong module EKS, kèm root Application (app-of-apps). Bỏ bước cài Argo CD trong `idp-gitops/scripts/bootstrap.*`.
4. Secret: giá trị thật lưu trong SSM Parameter Store (SecureString). Sau khi cluster lên, đưa vào cluster bằng External Secrets Operator (IRSA, quyền chỉ đọc) hoặc bằng script tạo Secret. Chọn cách đơn giản và ổn định hơn, ghi lý do. Không để Argo CD sync các manifest Secret có placeholder (`CHANGE_ME_BASE64`) đè lên secret thật.
5. Region `us-east-1` ở mọi nơi. Không ghi cứng account ID hay commit tag. Lấy từ biến hoặc output (`aws_caller_identity`), hoặc để CI ghi vào.
6. Image: CI push lên ECR (được giữ lại giữa các buổi lab) và commit tag vào values. `aws-up` không build lại image.

## Giai đoạn 0 — Sửa lỗi chặn (không cần AWS)
Sửa và kiểm chứng từng mục; ghi mã audit vào commit và context log.
- Terraform:
  - Gộp về một backend bucket. Sửa key `05-ecr` thành `03-ecr`.
  - Thêm `00-bootstrap` để tạo state bucket (state của module này để local, hoặc hướng dẫn import).
  - Tách rõ module nền (bootstrap, ECR, OIDC, SSM) với module tạo-huỷ (network, EKS, Backstage EC2).
  - Nối các module bằng `terraform_remote_state`, bỏ việc copy output bằng tay. Sửa tên output bị gọi sai (#3), bổ sung input còn thiếu (#4).
  - Thêm repo ECR `compliance-engine` (#9).
  - Biến cấu hình node để dễ chỉnh chi phí (instance type, số node, SPOT/ON_DEMAND).
- GitOps:
  - Sửa `repoURL` và path của toàn bộ Application (#1, #7). Sync-wave đúng thứ tự.
  - Autoscaler: sửa region, role ARN lấy từ output (#8).
  - Image của compliance-engine (#19). Secret: key name khớp với Deployment (#17).
  - `ui` bỏ `type: LoadBalancer`, dùng ClusterIP + port-forward. Nếu thật sự cần truy cập ngoài thì dùng một Ingress/LB duy nhất, có bước dọn rõ ràng trong `aws-down`.
  - Tên Application khớp với annotation của Backstage catalog (#11, #25).
  - PostgreSQL cho compliance engine trên EKS (#18): đề xuất dùng PostgreSQL riêng trong namespace compliance, quản lý bằng GitOps.
- CI: thống nhất một tên secret cho cập nhật GitOps, áp dụng cho cả 5 workflow lẫn template (#10). Role ARN lấy từ secret, không ghi cứng.
- Compliance engine:
  - Sửa build-backend (#13).
  - Bỏ `await` trước `config.load_incluster_config()` trong `app/main.py`.
  - Sửa lỗi cú pháp ở `tests/test_scorer/test_engine.py`, và test `test_normalize_all_returns_only_valid`.
  - Migration chạy được từ DB trắng, chọn một trong hai: Alembic hoặc `create_all` (#14).
  - `POST /scans` phải có body (#15), cả trong script lẫn tài liệu.
  - Parser kube-bench: kiểm tra kiểu dữ liệu trước khi gọi `.get()`.
  - Dedup key và finding ID của Trivy phải có namespace, container và package.
- Backstage:
  - Thống nhất port và URL (#23).
  - Proxy tới compliance engine phải có đường đi thật từ EC2 tới EKS (#24).
  - Đăng ký template trong catalog (#26).
  - Nối đúng API contract giữa backend và plugin theo audit mục 5.1, sửa ở hai phía hoặc thêm lớp chuyển đổi trong client. Dashboard có empty state khi chưa có scan.
- Chưa làm trong đợt này (ghi vào phần "còn lại", trừ khi việc đó chặn smoke test): mở rộng rule lên ≥20, đo chất lượng AI, tách điểm theo workload (audit 5.2–5.4).

## Giai đoạn 1 — CI kiểm tra tĩnh
- `.github/workflows/validate.yml` chạy cho mọi PR và mọi lần push:
  - `terraform fmt -check`, `init -backend=false` + `validate` cho từng module, `tflint`.
  - `helm lint` + `helm template` cho chart microservice với values của từng app; `kustomize build` các overlay; tất cả đưa qua `kubeconform` (có CRD schema cho Argo CD, Kyverno, Trivy, Prometheus).
  - `kyverno test` hoặc `kyverno apply` 8 policy với workload A/B/C (kỳ vọng A vi phạm, B pass).
  - `pytest` compliance-engine (Python 3.12, cài từ pyproject); `tsc --noEmit` cho plugin Backstage.
  - `docker build` 6 image (5 service + compliance-engine), không push.
  - Bước chặn placeholder: `YOUR_ORG`, `YOUR_ECR_REGISTRY`, `CHANGE_ME`, `ap-southeast-1`, account ID ghi cứng.
  - Pin version mọi tool và action.
- `scripts/validate-local.sh`: chỉ các bước nhẹ chạy được trên máy (terraform fmt/validate, tflint, pytest, tsc, grep placeholder). Chạy được bằng Git Bash.
- Chạy validate-local trên máy cho tới khi pass. Phần CI chỉ chạy khi tôi đồng ý push branch; sau đó đọc kết quả bằng `gh run view` (nếu có gh) hoặc tôi dán log lại.

## Giai đoạn 2 — Smoke test compliance engine trong CI (không cần cluster)
- Thêm chế độ collector đọc từ file fixture (PolicyReport, VulnerabilityReport, kube-bench JSON mô phỏng workload A/B/C trong compliance-engine/fixtures). Bật bằng biến môi trường; mặc định vẫn đọc từ Kubernetes.
- Job CI `engine-smoke`:
  1. docker compose up (API + PostgreSQL + Redis, DB trắng, đúng cơ chế migration đã chọn).
  2. `POST /api/v1/scans` có body, rồi poll tới completed.
  3. `GET /scores` và `/findings` có dữ liệu.
  4. Gọi recommendation rule-based cho một finding.
  5. Kiểm tra response khớp kiểu dữ liệu plugin Backstage kỳ vọng.
  6. Upload evidence làm artifact.
- Phần chỉ chạy được trên cluster (Argo CD sync, scanner sinh report thật, CronJob gọi scan, NetworkPolicy, probe của workload A/B/C): chỉ kiểm tĩnh ở giai đoạn 1, và liệt kê các lỗi dự kiến để kiểm ở giai đoạn 3.

## Giai đoạn 3 — Script AWS và kiểm thử thật trên EKS
- `scripts/aws-foundation-up.sh`: tạo lớp nền, idempotent, chạy một lần. Kèm hướng dẫn nạp secret vào SSM.
- `scripts/aws-up.sh`:
  1. VPC → EKS (+ Argo CD + root app).
  2. Nạp secret từ SSM.
  3. Chờ các Argo app Healthy/Synced.
  4. Chạy `smoke.sh`.
  5. In URL và lệnh port-forward.
- `scripts/aws-down.sh`, thứ tự bắt buộc:
  1. Xoá root Application theo kiểu cascade.
  2. Chờ các Service LoadBalancer và PVC bị xoá hết, kiểm tra không còn ELB/EBS gắn với cluster.
  3. Destroy Backstage EC2 → EKS → VPC.
  4. Kiểm tra lại không còn ELB, EBS, ENI hay NAT mồ côi.
  KHÔNG đụng vào lớp nền.
- `scripts/smoke.sh` (chạy với cluster EKS):
  - Mọi Argo app Healthy.
  - Có PolicyReport, VulnerabilityReport và kết quả kube-bench.
  - Scan → score/finding cho workload A/B/C → rule recommendation.
  - Lưu evidence (scan ID, timestamp, image digest, thời gian từng bước) vào docs/evidence/aws/.
- Tất cả script có `--dry-run` (terraform plan, không tạo gì), chạy được bằng Git Bash và Linux. kubectl/helm gọi qua Docker image hoặc chạy trong CloudShell.
- Kiểm thử thật: sau khi tôi xác nhận, chạy `aws-up` → `smoke.sh` → sửa lỗi phát sinh → `aws-down`. Lặp tới khi smoke pass. Lần nào cũng phải kết thúc bằng `aws-down`, trừ khi tôi nói giữ lại. Ghi tiến độ vào progress file trước mỗi lệnh tốn tiền.

## Giai đoạn 4 — Tài liệu
Viết lại docs/SETUP.md ngắn gọn, xoay quanh các script:
- Prerequisites (tool trong C:\tools, lệnh kiểm tra phiên bản).
- Lớp nền (một lần).
- Vòng lab: `aws-up` → làm việc → `aws-down`.
- CI và cách đọc kết quả.
- Xử lý khi bị dừng giữa chừng: kiểm tra tài nguyên còn sót bằng `aws-down --dry-run` và AWS Console.
- Troubleshooting từ các lỗi đã gặp thật.
- Bảng chi phí theo cấu hình thật trong Terraform: phần tính theo giờ và phần gần 0 vì được giữ lại.
Không sửa file audit; ghi trong context log những mục audit đã xử lý.

## Kết quả cần báo lại
- Bảng các mục audit (#1–#27, mục 5.x) và các lỗi bổ sung (ECR bị xoá mỗi lần destroy; Service LoadBalancer của `ui`; PVC/EBS mồ côi; account ID và image tag ghi cứng; các module không nối với nhau; bảng chi phí sai cấu hình). Mỗi mục ghi: đã sửa / kiểm chứng bằng cách nào (máy, CI hay AWS) / còn lại và vì sao.
- Kết quả validate-local, CI và smoke trên EKS (output rút gọn), kèm thời gian dựng và huỷ.
- Rủi ro còn lại và việc cần tôi quyết định.
