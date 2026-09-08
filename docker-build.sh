#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

WORKSPACE="$intro_root" \
NAME="${NAME:-tardigrade-intro-controls}" \
"$intro_root/tardigrade_ws/docker-build.sh" "$@"
