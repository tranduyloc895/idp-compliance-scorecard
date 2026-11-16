#!/usr/bin/env bash
# Ghi ECR registry + image tag của một service vào idp-gitops (CI gọi sau khi push).
#   scripts/ci-set-image.sh <service> <registry> <tag>
# Retail Store: apps/image-registry.yaml (registry) + apps/<svc>/values.yaml (tag)
# compliance-engine: compliance/compliance-engine/kustomization.yaml (images:)
set -euo pipefail

svc="${1:?service}"
registry="${2:?registry}"
tag="${3:?tag}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/idp-gitops"

command -v yq >/dev/null || { echo "yq is required"; exit 1; }

case "$svc" in
  ui|cart|catalog|orders|checkout)
    REGISTRY="$registry" yq -i '.image.registry = strenv(REGISTRY)' "$root/apps/image-registry.yaml"
    TAG="$tag" yq -i '.image.tag = strenv(TAG)' "$root/apps/$svc/values.yaml"
    ;;
  compliance-engine)
    NEWNAME="$registry/retail-store/compliance-engine" TAG="$tag" yq -i \
      '(.images[] | select(.name == "compliance-engine")) |= (.newName = strenv(NEWNAME) | .newTag = strenv(TAG))' \
      "$root/compliance/compliance-engine/kustomization.yaml"
    ;;
  *)
    echo "unknown service: $svc"; exit 1 ;;
esac
echo "set $svc -> $registry/retail-store/$svc:$tag"
