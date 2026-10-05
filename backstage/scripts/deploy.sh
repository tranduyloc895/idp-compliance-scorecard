#!/bin/bash
# ============================================================
#  deploy.sh — Deploy Backstage IDP Portal to EC2
#
#  Usage:
#    chmod +x scripts/deploy.sh
#    ./scripts/deploy.sh <elastic-ip>
#
#  Prerequisites:
#    - SSH key pair OR SSM Session Manager access
#    - .env file filled in (see .env.example)
#    - EC2 instance running (terraform apply in 05-backstage-ec2/)
# ============================================================
set -euo pipefail

ELASTIC_IP="${1:-}"
APP_DIR="/opt/backstage"
REPO_URL="https://github.com/tranduyloc895/idp-platform.git"  # adjust if needed
BACKSTAGE_SUBDIR="backstage"

# ─── Validate ──────────────────────────────────────────────
if [ -z "${ELASTIC_IP}" ]; then
  echo "Usage: $0 <elastic-ip>"
  echo ""
  echo "Get the IP from: cd infrastructure/05-backstage-ec2 && terraform output elastic_ip"
  exit 1
fi

echo "🚀 Deploying Backstage to EC2 @ ${ELASTIC_IP}..."

# ─── Step 1: Check SSH connectivity ────────────────────────
echo ""
echo "=== Step 1: Checking SSH connectivity ==="
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "ec2-user@${ELASTIC_IP}" "echo 'SSH OK'" 2>/dev/null; then
  echo "⚠️  SSH failed. Trying SSM Session Manager..."
  echo ""
  echo "Run manually via SSM:"
  echo "  aws ssm start-session --target <instance-id>"
  echo ""
  echo "Then inside the instance, run:"
  echo "  cd ${APP_DIR} && bash scripts/deploy-local.sh"
  exit 1
fi

# ─── Step 2: Clone or update repo ──────────────────────────
echo ""
echo "=== Step 2: Clone / update repo ==="
ssh "ec2-user@${ELASTIC_IP}" bash <<EOF
set -euo pipefail
if [ -d "${APP_DIR}/.git" ]; then
  echo "Pulling latest changes..."
  cd "${APP_DIR}"
  git pull --rebase
else
  echo "Cloning repository..."
  git clone "${REPO_URL}" /tmp/idp-platform-clone
  cp -r /tmp/idp-platform-clone/${BACKSTAGE_SUBDIR}/. "${APP_DIR}/"
  rm -rf /tmp/idp-platform-clone
fi
EOF

# ─── Step 3: Copy .env if not present ──────────────────────
echo ""
echo "=== Step 3: Environment variables ==="
if ! ssh "ec2-user@${ELASTIC_IP}" "test -f ${APP_DIR}/.env"; then
  echo "📋 .env not found on EC2. Creating from template..."
  scp .env.example "ec2-user@${ELASTIC_IP}:${APP_DIR}/.env"
  echo ""
  echo "⚠️  IMPORTANT: Edit the .env file on the EC2 instance before continuing!"
  echo "  ssh ec2-user@${ELASTIC_IP}"
  echo "  nano ${APP_DIR}/.env"
  echo ""
  read -r -p "Press Enter after you've filled in the .env file..." _
else
  echo "✅ .env already exists on EC2"
fi

# ─── Step 4: Build + start docker compose ──────────────────
echo ""
echo "=== Step 4: docker compose build && up ==="
ssh "ec2-user@${ELASTIC_IP}" bash <<EOF
set -euo pipefail
cd "${APP_DIR}"
echo "Building images..."
docker compose build --no-cache

echo "Starting services..."
docker compose up -d

echo "Waiting for health checks..."
sleep 30
docker compose ps
EOF

# ─── Step 5: Health check ──────────────────────────────────
echo ""
echo "=== Step 5: Health check ==="
MAX_RETRIES=10
RETRY=0
until curl -sf "http://${ELASTIC_IP}:7007/api/health" > /dev/null 2>&1; do
  RETRY=$((RETRY + 1))
  if [ ${RETRY} -ge ${MAX_RETRIES} ]; then
    echo "❌ Health check failed after ${MAX_RETRIES} retries"
    echo "Check logs: ssh ec2-user@${ELASTIC_IP} 'cd ${APP_DIR} && docker compose logs backstage'"
    exit 1
  fi
  echo "Waiting for Backstage API... (attempt ${RETRY}/${MAX_RETRIES})"
  sleep 15
done

echo ""
echo "✅ Backstage is running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  UI:      http://${ELASTIC_IP}:3000"
echo "  API:     http://${ELASTIC_IP}:7007/api/health"
echo "  Logs:    ssh ec2-user@${ELASTIC_IP} 'docker compose -f ${APP_DIR}/docker-compose.yml logs -f'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
