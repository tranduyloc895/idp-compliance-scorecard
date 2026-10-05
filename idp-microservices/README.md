# IDP Platform — Microservices

Source code cho 5 microservices của ứng dụng Retail Store demo.

## Services

| Service | Language | Port |
|---|---|---|
| `ui` | Java 21 (Spring Boot) | 8080 |
| `catalog` | Go | 8080 |
| `cart` | Java 21 (Spring Boot) | 8080 |
| `orders` | Java 21 (Spring Boot) | 8080 |
| `checkout` | TypeScript (NestJS) | 8080 |

## CI/CD

Mỗi service có GitHub Actions workflow tại `.github/workflows/ci-<service>.yml`.

Pipeline: `Build → Trivy scan → Push ECR → Update image tag in idp-gitops`

## Local Development

```bash
# Chạy toàn bộ stack locally bằng Docker Compose
cd src/app && docker compose up
```
