# ============================================================
#  Backstage IDP Portal — Multi-stage Dockerfile
#  Stage 1: install + build
#  Stage 2: runtime (lean image)
# ============================================================

# ─── Stage 1: Build ─────────────────────────────────────────
FROM node:20-bookworm-slim AS build

# Install system deps needed for native node modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    g++ \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Enable Corepack for Yarn
RUN corepack enable

WORKDIR /app

# Copy workspace manifests first (better layer caching)
COPY package.json yarn.lock .yarnrc.yml ./
COPY .yarn ./.yarn

# Install dependencies (frozen lockfile for reproducibility)
RUN yarn install --immutable

# Copy full source
COPY . .

# Build frontend + backend bundles
RUN yarn build:all

# ─── Stage 2: Runtime ───────────────────────────────────────
FROM node:20-bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN addgroup --system backstage && adduser --system --ingroup backstage backstage

WORKDIR /app

# Copy only what's needed to run
COPY --from=build --chown=backstage:backstage /app/packages/backend/dist ./dist
COPY --from=build --chown=backstage:backstage /app/packages/backend/node_modules ./node_modules
COPY --from=build --chown=backstage:backstage /app/node_modules ./node_modules
COPY --chown=backstage:backstage app-config.yaml ./app-config.yaml
COPY --chown=backstage:backstage app-config.production.yaml ./app-config.production.yaml
COPY --chown=backstage:backstage catalog ./catalog
COPY --chown=backstage:backstage templates ./templates

USER backstage

ENV NODE_ENV=production

EXPOSE 7007

CMD ["node", "dist/index.js", \
     "--config", "app-config.yaml", \
     "--config", "app-config.production.yaml"]
