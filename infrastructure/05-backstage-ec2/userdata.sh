#!/bin/bash
# ============================================================
#  Backstage EC2 User Data — Amazon Linux 2023
#  Runs once on first boot. Installs Docker + docker-compose.
# ============================================================
set -euo pipefail
exec > >(tee /var/log/userdata.log | logger -t userdata -s 2>/dev/console) 2>&1

echo "=== [userdata] Starting setup $(date) ==="

# ─── 1. System update ──────────────────────────────────────
dnf update -y

# ─── 2. Install Git ────────────────────────────────────────
dnf install -y git

# ─── 3. Install Docker (Amazon Linux 2023 uses dnf) ───────
dnf install -y docker

# Enable + start Docker
systemctl enable docker
systemctl start docker

# Allow ec2-user to use Docker without sudo
usermod -aG docker ec2-user

# ─── 4. Install Docker Compose v2 plugin ──────────────────
COMPOSE_VERSION="v2.27.1"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Symlink for legacy `docker-compose` command
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# ─── 5. Install SSM Agent (pre-installed on AL2023, ensure it's running) ──
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# ─── 6. Create app directory ───────────────────────────────
APP_DIR="/opt/backstage"
mkdir -p "${APP_DIR}"
chown ec2-user:ec2-user "${APP_DIR}"

# ─── 7. Install AWS CLI v2 (pre-installed on AL2023 AMI) ──
# Verify and print version
aws --version || echo "AWS CLI not found — install manually"

echo "=== [userdata] Setup complete $(date) ==="
echo "Next steps:"
echo "  1. SSH / SSM into instance"
echo "  2. cd /opt/backstage && git clone <repo> ."
echo "  3. cp .env.example .env && edit .env"
echo "  4. docker compose up -d"
