# Module 04-oidc — GitHub Actions OIDC IAM Role

## Mục đích

Tạo IAM OIDC Identity Provider và IAM Role cho phép GitHub Actions
authenticate với AWS **mà không cần static access key**.

Luồng: `GitHub Actions job → OIDC token → STS AssumeRoleWithWebIdentity → IAM Role → ECR`

---

## Bước 0 — Tạo S3 bucket cho Terraform state (làm 1 lần)

Bucket này dùng chung cho tất cả module trong `idp-infrastructure`.
Chạy lệnh sau (thay `<AWS_ACCOUNT_ID>` nếu muốn đổi tên):

```bash
# Tạo bucket (us-east-1 không cần --create-bucket-configuration)
aws s3api create-bucket \
  --bucket idp-platform-tfstate-tranduyloc895 \
  --region us-east-1

# Bật versioning (khôi phục tfstate khi có lỗi)
aws s3api put-bucket-versioning \
  --bucket idp-platform-tfstate-tranduyloc895 \
  --versioning-configuration Status=Enabled

# Bật server-side encryption
aws s3api put-bucket-encryption \
  --bucket idp-platform-tfstate-tranduyloc895 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket idp-platform-tfstate-tranduyloc895 \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

> **Lưu ý:** Nếu muốn dùng cùng bucket này cho module 01, 02, 03 — cập nhật
> lại `provider.tf` trong mỗi module để đổi tên bucket tương ứng.

---

## Bước 1 — Khởi tạo và apply

```bash
cd infrastructure/04-oidc

terraform init

# ecr_account_id = AWS Account ID của bạn (12 chữ số)
terraform apply -var="ecr_account_id=<YOUR_AWS_ACCOUNT_ID>"
```

Sau khi apply thành công:

```bash
terraform output role_arn
# → arn:aws:iam::<ACCOUNT_ID>:role/github-actions-idp-microservices
```

---

## Bước 2 — Set GitHub Secrets trên repo `idp-microservices`

Vào: **GitHub → tranduyloc895/idp-microservices → Settings → Secrets → Actions**

| Secret name | Giá trị |
|---|---|
| `AWS_ROLE_ARN` | Output `role_arn` từ bước trên |
| `AWS_ACCOUNT_ID` | AWS Account ID (12 chữ số) |
| `GITOPS_PAT` | GitHub PAT với quyền `repo` trên `idp-gitops` |

### Tạo GitHub PAT (GITOPS_PAT)

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Repository access: chỉ chọn `tranduyloc895/idp-gitops`
3. Permissions: **Contents** = Read and write
4. Copy token và lưu vào secret `GITOPS_PAT`

---

## Inputs

| Variable | Default | Mô tả |
|---|---|---|
| `aws_region` | `us-east-1` | Region |
| `github_org` | `tranduyloc895` | GitHub org/username |
| `github_repo` | `idp-microservices` | Repo name |
| `ecr_account_id` | *(bắt buộc)* | AWS Account ID |
| `iam_role_name` | `github-actions-idp-microservices` | Tên IAM Role |

## Outputs

| Output | Mô tả |
|---|---|
| `role_arn` | Dùng làm giá trị GitHub Secret `AWS_ROLE_ARN` |
| `oidc_provider_arn` | ARN của OIDC Provider |
| `role_name` | Tên IAM Role |
