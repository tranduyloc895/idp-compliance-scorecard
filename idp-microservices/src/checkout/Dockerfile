# ============================================================
# Stage 1: Build (Node + Yarn)
# ============================================================
FROM node:20-alpine AS build

WORKDIR /usr/src/app

# Cache deps layer: chỉ invalidate khi package.json/yarn.lock/.yarn đổi
# .yarn/releases/yarn-4.11.0.cjs phải có sẵn vì .yarnrc.yml trỏ yarnPath đến nó
COPY package.json yarn.lock .yarnrc.yml ./
COPY .yarn ./.yarn
RUN corepack enable \
    && yarn install --immutable

# Copy source & build (tsc → dist/)
COPY . .
RUN yarn build

# ============================================================
# Stage 2: Runtime (minimal)
# ============================================================
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

RUN dnf --setopt=install_weak_deps=False install -q -y \
    nodejs20 \
    shadow-utils \
    && dnf clean all

RUN alternatives --install /usr/bin/node node /usr/bin/node-20 90

# Non-root user UID 10001 (chuẩn dự án)
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --home /app --create-home appuser

WORKDIR /app

# Chỉ copy artifact cần runtime: node_modules (production) + dist
COPY --chown=appuser:appuser --from=build /usr/src/app/node_modules ./node_modules
COPY --chown=appuser:appuser --from=build /usr/src/app/dist         ./dist

ENV NODE_ENV=production

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["node", "dist/main.js"]
