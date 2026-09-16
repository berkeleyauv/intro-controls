#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# ROS Foxy images are amd64-only on many registries. Docker Desktop and
# OrbStack can emulate them on Apple Silicon.
if [[ "$(uname -m)" == "arm64" && -z "${DOCKER_DEFAULT_PLATFORM:-}" ]]; then
  export DOCKER_DEFAULT_PLATFORM=linux/amd64
  echo "Apple Silicon detected; using Docker platform linux/amd64."
fi

WORKSPACE="$intro_root" \
NAME="${NAME:-tardigrade-intro-controls}" \
"$intro_root/tardigrade_ws/docker-build.sh" "$@"
