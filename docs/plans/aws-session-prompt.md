# Prompt mở đầu buổi kiểm thử trên AWS

Dán nguyên văn phần dưới đây vào đoạn chat mới (Claude Code, thư mục `C:\workspace\it\project\idp-compliance-scorecard`).

---

Tiếp tục dự án IDP Compliance Scorecard: buổi này chuyển sang dựng và kiểm thử trên AWS. Kế hoạch gốc ở `docs/plans/testable-rebuild.md` (Giai đoạn 3–4); các ràng buộc và "Quyết định đã chốt" trong file đó vẫn giữ nguyên hiệu lực.

## Nắm context trước khi làm gì (bắt buộc, theo thứ tự)
1. `CLAUDE.md`
2. `context/2026-11-15_testable-rebuild-progress.md`: checklist, quyết định đã chốt kèm lý do, bảng kết quả CI, "Bước tiếp theo".
3. `context/2026-11-15_phase0-blocking-fixes.md`, `context/2026-11-15_phase1-2-static-ci-smoke.md`, `context/2026-11-15_phase3-4-aws-scripts-docs.md`
4. `docs/SETUP.md` (runbook mới, bảng chi phí) và `docs/plans/testable-rebuild.md`
5. Các script sẽ chạy: `scripts/lib.sh`, `scripts/aws-foundation-up.sh`, `scripts/aws-up.sh`, `scripts/aws-down.sh`, `scripts/smoke.sh`, `scripts/k8s-secrets.sh`, `scripts/ssm-put-secrets.sh`
6. Chạy `git status`, `git log --oneline -15`, `gh pr view 1 --repo tranduyloc895/idp-compliance-scorecard`.
7. Dùng `graphify query` trước khi grep code.

Sau khi đọc xong, tóm tắt lại cho tôi trong 5–8 dòng: trạng thái hiện tại và bước đầu tiên định làm. Chưa chạy lệnh AWS nào trước khi tôi xác nhận.

## Trạng thái khi kết thúc buổi trước (2026-11-15)
- Branch `feat/testable-rebuild`, PR #1 vào `main`. CI `validate` pass 14/14 (run 43715994569). `validate-local.sh` pass trên máy.
- Chưa có tài nguyên AWS nào được tạo. Chưa chạy `terraform plan` với credential.
- Argo CD theo dõi `main`, nên PR #1 phải được merge trước khi kiểm trên EKS. Nếu PR chưa merge thì hỏi tôi; không tự merge.
- Sau khi merge, workflow `ci-compliance-engine` trên `main` sẽ fail cho tới khi có secret `AWS_ROLE_ARN`. Đây là lỗi đã biết.
- GitOps đang để `ECR_REGISTRY_NOT_SET` và tag `not-built` cho tới khi workflow `build-all` chạy. Preflight của `aws-up` sẽ dừng nếu chưa có image.

## Môi trường
- Windows 11, Git Bash. Tool ở `C:\tools\*`: terraform 1.11.4, node 20.18.0, gh 2.62.0 (đã login `tranduyloc895`), aws-cli 2.22.0. Python 3.12 ở `C:\tools\python`.
- Windows Application Control chặn `terraform-provider-*.exe`, nên **mọi lệnh terraform và script `aws-*.sh`/`smoke.sh` phải chạy trong WSL `Ubuntu-22.04`**. Repo trong WSL nằm ở `/mnt/c/workspace/it/project/idp-compliance-scorecard`; terraform và tflint ở `~/tools/bin`.
- Gọi WSL từ Git Bash: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/.../<file>.sh`. `wsl.exe` tự expand `$VAR` trong tham số, nên không truyền chuỗi lệnh có `$`. Hãy viết lệnh vào một file script (trong scratchpad hoặc repo) rồi gọi file đó.
- Credential: tôi đã chạy `aws configure --profile idp-lab` **trong WSL** (region `us-east-1`). Script dùng `export AWS_PROFILE=idp-lab`. Không yêu cầu tôi dán key vào chat; không in key ra log.
- kubectl: "cho phép cài kubectl v1.35.0 vào ~/tools/bin trong WSL"

## Quy tắc buổi này
- Đầu buổi chạy `aws sts get-caller-identity` (profile `idp-lab`, trong WSL) và báo account ID/ARN cho tôi xác nhận.
- Luôn `--dry-run` trước (chỉ plan/liệt kê), cho tôi xem tóm tắt plan (số resource add/change/destroy và các resource tốn tiền), rồi **hỏi** trước khi chạy thật.
- Trước mỗi lệnh tạo tài nguyên hoặc tốn tiền: ghi vào progress file (lệnh, thời điểm, chi phí ước tính) và commit.
- Buổi lab **luôn kết thúc bằng `bash scripts/aws-down.sh`**, rồi kiểm không còn tài nguyên mồ côi, trừ khi tôi nói giữ lại. Nếu phải dừng giữa chừng: chạy `aws-down.sh --dry-run` để liệt kê còn gì, báo tôi, ghi "Bước tiếp theo".
- Không destroy lớp nền (S3 state, ECR, OIDC, SSM).
- Hỏi trước khi: merge PR, `gh secret set`, chạy workflow `build-all`, push lên `main`. Push lên `feat/testable-rebuild` hoặc branch sửa lỗi thì được.
- Lỗi phát sinh: sửa trong code/script, kiểm lại bằng `validate-local.sh` (và CI nếu sửa manifest), commit nhỏ, message ghi mã audit nếu có. Ghi lỗi đã gặp thật vào mục Troubleshooting của `docs/SETUP.md`.
- Không sửa `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`. Sau mỗi giai đoạn: viết context log theo quy ước trong `CLAUDE.md` và chạy `graphify update .`.

## Trình tự dự kiến
1. Chuẩn bị WSL: kiểm `aws --version`, terraform, (kubectl nếu được phép); `aws sts get-caller-identity`.
2. Lớp nền: `aws-foundation-up.sh --dry-run` → tôi xác nhận → chạy thật. Lưu output `role_arn`, `registry`, tên state bucket vào progress file (không lưu secret).
3. GitHub: hỏi tôi rồi `gh secret set AWS_ROLE_ARN`, kiểm Workflow permissions = Read and write. Sau khi PR #1 đã merge, chạy workflow `build-all` trên `main`, theo dõi bằng `gh run watch`, sửa lỗi nếu Trivy gate hoặc build fail. Kiểm CI đã ghi registry/tag vào GitOps.
4. Lớp tạo-huỷ: `aws-up.sh --dry-run` → xác nhận → `aws-up.sh` (gồm `smoke.sh`). Ghi thời gian dựng.
5. Sửa lỗi smoke cho tới khi pass. Những điểm chưa kiểm chứng cần để ý:
   - chart 2024 (kyverno 3.2.6, trivy-operator 0.24.1, kube-prometheus-stack 58, loki 6.6, Argo CD 5.51.4) trên K8s 1.35;
   - sync-wave và health của Application;
   - internal Classic LB `compliance-engine-internal`;
   - `kube-bench v0.8.0 --benchmark eks-1.2.0`;
   - image `cluster-autoscaler v1.35.0`;
   - tài nguyên 2× t3.large đủ cho monitoring stack;
   - thời gian Trivy sinh VulnerabilityReport;
   - workload B/C Ready.
6. `aws-down.sh`, kiểm mồ côi, ghi thời gian huỷ. Lưu evidence ở `docs/evidence/aws/`.
7. Cập nhật `docs/SETUP.md` (troubleshooting thật, thời gian dựng/huỷ), progress file, context log.

## Báo lại cuối buổi
- Bảng các mục audit kèm trạng thái: đã sửa, kiểm chứng bằng cách nào (máy/CI/AWS), còn lại và vì sao.
- Output rút gọn của `aws-foundation-up`, `build-all`, `aws-up`, `smoke`, `aws-down`; thời gian dựng và huỷ.
- Tài nguyên còn lại trên AWS (lớp nền) và chi phí ước tính của buổi.
- Rủi ro còn lại và việc cần tôi quyết định.
