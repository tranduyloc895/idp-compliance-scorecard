#!/usr/bin/env bash
# Cài tool pin version vào ~/bin trong AWS CloudShell (hoặc Linux x86_64 bất kỳ).
# KHÔNG dùng trên máy dev Windows (quy ước: không cài kubectl/helm lên máy).
#
#   bash scripts/cloudshell-tools.sh && export PATH=$HOME/bin:$PATH
set -euo pipefail
TERRAFORM_VERSION="${TERRAFORM_VERSION:-1.11.4}"
KUBECTL_VERSION="${KUBECTL_VERSION:-v1.35.0}"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ;;
  *) echo "Chỉ hỗ trợ Linux x86_64 (CloudShell). Trên Windows dùng CloudShell."; exit 1 ;;
esac

mkdir -p "$HOME/bin"
cd "$(mktemp -d)"

if ! "$HOME/bin/terraform" version 2>/dev/null | grep -q "v${TERRAFORM_VERSION}"; then
  curl -fsSLo tf.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
  python3 -c 'import zipfile,os; zipfile.ZipFile("tf.zip").extract("terraform", os.path.expanduser("~/bin"))'
  chmod +x "$HOME/bin/terraform"
fi

if ! "$HOME/bin/kubectl" version --client 2>/dev/null | grep -q "${KUBECTL_VERSION}"; then
  curl -fsSLo kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  curl -fsSLo kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256"
  echo "$(cat kubectl.sha256)  kubectl" | sha256sum -c -
  install -m 0755 kubectl "$HOME/bin/kubectl"
fi

"$HOME/bin/terraform" version | head -1
"$HOME/bin/kubectl" version --client | head -1
aws --version
echo 'Thêm vào PATH: export PATH=$HOME/bin:$PATH'
