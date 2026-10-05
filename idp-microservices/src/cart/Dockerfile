# ============================================================
# Stage 1: Build
# ============================================================
FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS build-env

RUN dnf --setopt=install_weak_deps=False install -q -y \
    java-21-amazon-corretto-headless \
    which tar gzip \
    && dnf clean all

WORKDIR /workspace

# Cache dependencies layer: chỉ invalidate khi pom.xml / mvn wrapper đổi
COPY .mvn .mvn
COPY mvnw .
COPY pom.xml .
RUN chmod +x mvnw && ./mvnw dependency:go-offline -B -q

# Copy source và build
COPY ./src ./src
RUN ./mvnw -DskipTests package -q \
    && mv target/carts-0.0.1-SNAPSHOT.jar /app.jar

# ============================================================
# Stage 2: Runtime (minimal JRE)
# ============================================================
FROM public.ecr.aws/amazonlinux/amazonlinux:2023

RUN dnf --setopt=install_weak_deps=False install -q -y \
    java-21-amazon-corretto-headless \
    shadow-utils \
    && dnf clean all

# Non-root user UID 10001 (theo chuẩn dự án)
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --home /app --create-home appuser

ENV SPRING_PROFILES_ACTIVE=prod
ENV JAVA_TOOL_OPTIONS=

WORKDIR /app

COPY --chown=appuser:appuser --from=build-env /app.jar /app/app.jar

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health/readiness || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -XX:MaxRAMPercentage=75.0 -Djava.security.egd=file:/dev/urandom -jar /app/app.jar"]
