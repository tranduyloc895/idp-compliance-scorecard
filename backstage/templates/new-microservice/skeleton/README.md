# ${{ values.serviceName | title }}

> ${{ values.description }}

## Overview

| | |
|---|---|
| **Language** | ${{ values.language }} |
| **Owner** | ${{ values.owner }} |
| **System** | [Retail Store Platform](https://github.com/tranduyloc895) |
| **Created** | via Backstage Golden Path Template |

## Getting Started

### Prerequisites

- Docker
- AWS CLI (configured with ECR access)
- `GITOPS_TOKEN` secret set in GitHub repository settings

### Local Development

```bash
# Clone this repository
git clone https://github.com/tranduyloc895/${{ values.serviceName }}.git
cd ${{ values.serviceName }}

# Build and run
docker build -t ${{ values.serviceName }}:local .
docker run -p 8080:8080 ${{ values.serviceName }}:local
```

### CI/CD Pipeline

The CI pipeline (`.github/workflows/ci.yml`) runs on every push to `main`:

1. **OIDC Auth** → Authenticates to AWS without static credentials
2. **Docker Build** → Builds the container image
3. **Trivy Scan** → Scans for CRITICAL/HIGH CVEs
4. **ECR Push** → Pushes image to `${{ values.ecrRegistry }}/${{ values.ecrRepo }}`
5. **GitOps Update** → Updates `apps/${{ values.serviceName }}/values.yaml` in `idp-gitops`

### First Deployment

After the CI runs successfully for the first time:

1. Merge the PR in [`idp-gitops`](https://github.com/tranduyloc895/idp-gitops)
2. ArgoCD will automatically sync and deploy the service to EKS

## Links

- [Backstage Catalog](http://backstage) — service details, CI runs, ArgoCD status
- [ECR Repository](https://us-east-1.console.aws.amazon.com/ecr/repositories/private/736508008585/${{ values.ecrRepo }})
- [GitHub Actions](https://github.com/tranduyloc895/${{ values.serviceName }}/actions)
