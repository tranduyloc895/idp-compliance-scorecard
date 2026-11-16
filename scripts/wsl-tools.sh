#!/usr/bin/env bash
# Cài tool cho buổi AWS vào ~/tools (không cần sudo). Chạy TRONG WSL Ubuntu-22.04:
#   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-22.04 -- bash /mnt/c/workspace/it/project/idp-compliance-scorecard/scripts/wsl-tools.sh
# Windows không chạy được terraform provider (Application Control) và không cài kubectl.
set -euo pipefail
KUBECTL_VERSION=v1.35.0
AWSCLI_VERSION=2.22.0
TF_VERSION=1.11.4
BIN="$HOME/tools/bin"
mkdir -p "$BIN"
TMP="$(mktemp -d)"; cd "$TMP"

unzip_py() { python3 - "$1" "$2" <<'PY'
import sys, zipfile, os
z = zipfile.ZipFile(sys.argv[1])
for info in z.infolist():
    path = z.extract(info, sys.argv[2])
    mode = (info.external_attr >> 16) & 0o777
    if mode:
        os.chmod(path, mode)
PY
}

# terraform (đã có từ trước; chỉ kiểm version)
if ! "$BIN/terraform" version 2>/dev/null | grep -q "v$TF_VERSION"; then
  curl -fsSLo tf.zip "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip"
  unzip_py tf.zip "$BIN"; chmod +x "$BIN/terraform"
fi

# kubectl (kiểm sha256)
if ! "$BIN/kubectl" version --client 2>/dev/null | grep -q "$KUBECTL_VERSION"; then
  curl -fsSLo kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  curl -fsSLo kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256"
  echo "$(cat kubectl.sha256)  kubectl" | sha256sum -c -
  install -m 0755 kubectl "$BIN/kubectl"
fi

# aws-cli v2 (installer chính thức, cài vào ~/tools/aws-cli, không sudo)
if ! "$BIN/aws" --version 2>/dev/null | grep -q "aws-cli/$AWSCLI_VERSION"; then
  curl -fsSLo awscli.zip "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWSCLI_VERSION}.zip"
  unzip_py awscli.zip "$TMP"
  "$TMP/aws/install" -i "$HOME/tools/aws-cli" -b "$BIN" --update
fi

# PATH cho shell tương tác (idempotent)
grep -q 'tools/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/tools/bin:$PATH"' >> "$HOME/.bashrc"

export PATH="$BIN:$PATH"
echo "--- versions"
set +o pipefail
terraform version | head -1
tflint --version | head -1
kubectl version --client | head -1
aws --version
git --version
python3 --version
command -v jq >/dev/null && jq --version || echo "jq: not installed (scripts do not need it)"
echo "--- aws profiles"
aws configure list-profiles 2>/dev/null || true
rm -rf "$TMP"
