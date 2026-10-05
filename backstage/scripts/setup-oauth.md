# GitHub OAuth App Setup Guide

Backstage dùng GitHub OAuth để authenticate users. Hướng dẫn này mô tả cách tạo OAuth App trên GitHub.

## Prerequisites

- Elastic IP của EC2 instance Backstage (lấy từ `terraform output elastic_ip`)
- Tài khoản GitHub `tranduyloc895`

## Bước 1: Tạo GitHub OAuth App

1. Truy cập: **https://github.com/settings/developers**
2. Click **"New OAuth App"**
3. Điền thông tin:

   | Field | Value |
   |---|---|
   | **Application name** | `IDP Portal — Retail Store` |
   | **Homepage URL** | `http://<elastic-ip>:3000` |
   | **Authorization callback URL** | `http://<elastic-ip>:7007/api/auth/github/handler/frame` |
   | **Enable Device Flow** | ✅ (optional, for CLI auth) |

   > ⚠️ Thay `<elastic-ip>` bằng IP thực từ `terraform output elastic_ip`

4. Click **"Register application"**

## Bước 2: Lấy Client ID và Secret

Sau khi tạo xong:
1. **Client ID** hiển thị ngay — copy lại
2. Click **"Generate a new client secret"** → copy secret (chỉ hiển thị 1 lần!)

## Bước 3: Cập nhật .env

SSH vào EC2 và chỉnh sửa `.env`:

```bash
ssh ec2-user@<elastic-ip>
cd /opt/backstage
nano .env
```

Cập nhật các giá trị:
```env
AUTH_GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxxxxxx
AUTH_GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Restart Backstage:
```bash
docker compose restart backstage
```

## Bước 4: Tạo GitHub Personal Access Token (PAT)

Backstage cần PAT để đọc catalog từ GitHub và cho Scaffolder tạo repos mới.

1. Truy cập: **https://github.com/settings/tokens?type=beta** (Fine-grained PAT)
2. Click **"Generate new token"**
3. Chọn permissions:
   - **Repository access**: All repositories (hoặc chọn từng repo)
   - **Repository permissions**:
     - Contents: Read & Write (để scaffolder push code)
     - Pull requests: Read & Write (để mở GitOps PR)
     - Workflows: Read & Write (để tạo CI workflows)
     - Metadata: Read-only
4. Copy token → cập nhật `.env`:

```env
GITHUB_TOKEN=github_pat_xxxxxxxx
```

## Bước 5: Xác minh

Sau khi restart Backstage, truy cập `http://<elastic-ip>:3000` và đăng nhập bằng GitHub.

## Callback URL Reference

| Environment | Callback URL |
|---|---|
| EC2 Production | `http://<elastic-ip>:7007/api/auth/github/handler/frame` |
| Local Dev | `http://localhost:7007/api/auth/github/handler/frame` |

> 💡 **Tip:** Elastic IP không thay đổi khi EC2 restart, nên Callback URL sẽ luôn ổn định.
