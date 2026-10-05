# ============================================================
# Stage 1: Build
# ============================================================
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS build-env

# Chỉ cài gói cần thiết, bỏ qua weak deps cho image gọn nhất
# gcc + glibc-devel cần để build go-sqlite3 (driver in-memory database mặc định) với CGO
RUN dnf --setopt=install_weak_deps=False install -q -y \
    git \
    golang \
    gcc \
    glibc-devel \
    && dnf clean all

WORKDIR /appsrc

ENV GOPROXY=https://goproxy.io,direct

# Cache dependencies layer: chỉ invalidate khi go.mod/go.sum đổi
COPY go.mod go.sum ./
RUN go mod download

COPY . .

# CGO_ENABLED=1 vì go-sqlite3 (in-memory mode) cần liên kết với SQLite C library.
# Binary sẽ link động với glibc → runtime image phải có glibc (amazonlinux:2023 đã có).
# Strip debug info bằng -ldflags="-s -w" để giảm size.
RUN CGO_ENABLED=1 go build -ldflags="-s -w" -o main main.go

# ============================================================
# Stage 2: Runtime (minimal image)
# ============================================================
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# curl-minimal đã có sẵn; chỉ cần shadow-utils để tạo user
RUN dnf --setopt=install_weak_deps=False install -q -y \
    shadow-utils \
    && dnf clean all

# Tạo non-root user với UID 10001 (tránh xung đột UID 1000 mặc định của 1 số base image)
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --home /app --create-home appuser

WORKDIR /app

COPY --chown=appuser:appuser --from=build-env /appsrc/main /app/

ENV GIN_MODE=release

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/app/main"]
