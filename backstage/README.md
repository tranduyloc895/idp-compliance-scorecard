# Backstage IDP Portal — Retail Store

Self-service developer portal chạy trên EC2, cung cấp Software Catalog, Golden Path Templates, và tích hợp ArgoCD + GitHub Actions cho toàn bộ Retail Store platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EC2 (t3.small)  ·  Elastic IP (fixed)                      │
│                                                              │
│  ┌──────────────────┐     ┌─────────────────────────────┐  │
│  │  Backstage :7007 │────▶│  PostgreSQL :5432 (Docker)  │  │
│  │  (Docker)        │     └─────────────────────────────┘  │
│  └──────────────────┘                                       │
│         ▲                                                    │
│   :3000 │ (UI)                                              │
└─────────│────────────────────────────────────────────────────┘
          │
    Browser / Developer
```

## Features

| Feature | Status | Description |
|---|---|---|
| **Software Catalog** | ✅ | 5 microservices + 1 System entity |
| **GitHub Actions plugin** | ✅ | CI run history per service |
| **ArgoCD plugin** | ✅ Config ready | Sync status (needs EKS — M1.3) |
| **GitHub PR plugin** | ✅ | Pull request list per service |
| **Golden Path Template** | ✅ | Create new microservice in 1 click |

## Prerequisites

- Docker + Docker Compose v2 installed on EC2 (automated via `userdata.sh`)
- GitHub OAuth App (see [`scripts/setup-oauth.md`](scripts/setup-oauth.md))
- GitHub Personal Access Token with `repo` + `workflow` scopes
- ArgoCD URL + token (optional — needed for ArgoCD plugin)

## Quick Start (Local Dev)

```bash
cd backstage/

# 1. Copy environment template
cp .env.example .env
# Edit .env with your values

# 2. Build and start
docker compose up -d

# 3. Open portal
open http://localhost:3000
```

## EC2 Deploy

### Step 1: Provision EC2

```bash
cd infrastructure/05-backstage-ec2/
terraform init
terraform apply

# Note the outputs:
terraform output elastic_ip            # → Use for OAuth callback URL
terraform output github_oauth_callback_url
```

### Step 2: Set up GitHub OAuth App

Follow [`scripts/setup-oauth.md`](scripts/setup-oauth.md).

### Step 3: Deploy

```bash
cd backstage/
chmod +x scripts/deploy.sh
./scripts/deploy.sh <elastic-ip>
```

The script will:
1. SSH into EC2
2. Clone/pull the repository
3. Prompt you to fill in `.env` if not present
4. `docker compose build && docker compose up -d`
5. Health-check `http://<elastic-ip>:7007/api/health`

## Directory Structure

```
backstage/
├── app-config.yaml              # Main Backstage config
├── app-config.production.yaml   # Production overrides
├── docker-compose.yml           # Backstage + PostgreSQL
├── Dockerfile                   # Multi-stage build
├── .env.example                 # Environment variables template
├── catalog/                     # Software Catalog entities
│   ├── all.yaml                 # Location manifest (entry point)
│   ├── system.yaml              # System: retail-store
│   ├── ui.yaml                  # Component: UI (Java/Spring Boot)
│   ├── catalog-svc.yaml         # Component: Catalog (Go)
│   ├── cart.yaml                # Component: Cart (Java/Spring Boot)
│   ├── orders.yaml              # Component: Orders (Java/Spring Boot)
│   └── checkout.yaml            # Component: Checkout (NestJS)
├── templates/
│   └── new-microservice/        # Golden Path Template
│       ├── template.yaml        # Template definition
│       └── skeleton/            # Generated service scaffold
└── scripts/
    ├── deploy.sh                # EC2 deploy script
    └── setup-oauth.md           # GitHub OAuth App setup guide
```

## Plugins

### ArgoCD (`@roadiehq/backstage-plugin-argo-cd`)

Shows sync status and resource tree for each service. Requires:
- `ARGOCD_URL` and `ARGOCD_AUTH_TOKEN` in `.env`
- EKS cluster running (Milestone 1.3)
- Annotation on entity: `argocd/app-name: <app-name>`

### GitHub Actions (`@backstage-community/plugin-github-actions`)

Shows CI workflow runs. Requires:
- `GITHUB_TOKEN` in `.env`
- Annotation on entity: `github.com/project-slug: tranduyloc895/<repo>`
- Annotation: `github.com/workflows: ci-<service>.yml`

## Golden Path Template

The **"Create a New Microservice"** template in Backstage Scaffolder:

1. Fills a form (service name, language, owner)
2. Generates source from `templates/new-microservice/skeleton/`
3. Creates a new GitHub repo: `tranduyloc895/<service-name>`
4. Opens a PR in `idp-gitops` with Helm values + ArgoCD Application
5. Registers the service in the Backstage Catalog

### After running the template (manual steps)

```bash
# 1. Add new repo to OIDC trust policy
cd infrastructure/04-oidc/
# Edit main.tf → add "repo:tranduyloc895/<service-name>:*" to condition
terraform apply

# 2. Create ECR repository
cd infrastructure/03-ecr/
# Add new repo definition
terraform apply

# 3. Merge the GitOps PR → ArgoCD deploys automatically
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `http://<ip>:3000` not reachable | Check Security Group inbound port 3000 |
| GitHub login fails | Verify OAuth callback URL matches Elastic IP |
| Catalog not loading | Check `GITHUB_TOKEN` has `repo` scope |
| ArgoCD tab empty | `ARGOCD_URL` / `ARGOCD_AUTH_TOKEN` not set, or EKS not up |
| `docker compose up` fails | Check `.env` has all required values |

### View logs

```bash
# SSH into EC2
ssh ec2-user@<elastic-ip>

# Backstage logs
cd /opt/backstage && docker compose logs -f backstage

# PostgreSQL logs
docker compose logs -f db
```

## Roadmap

- **Milestone 1.3**: EKS cluster up → ArgoCD plugin fully functional
- **Milestone 3**: Compliance Dashboard plugin
