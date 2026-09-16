#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
failed=false

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "ok: $1"
  else
    echo "missing: $1"
    failed=true
  fi
}

check_command git
check_command docker

if git lfs version >/dev/null 2>&1; then
  echo "ok: Git LFS"
else
  echo "missing: Git LFS (required for Unity assets)"
  failed=true
fi

if docker compose version >/dev/null 2>&1; then
  echo "ok: Docker Compose"
else
  echo "missing: Docker Compose plugin"
  failed=true
fi

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    echo "ok: Docker daemon"
  else
    echo "unavailable: Docker daemon (start Docker Desktop or OrbStack)"
    failed=true
  fi
fi

for port in 10000 9090; do
  if command -v lsof >/dev/null 2>&1 && \
      lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "in use: TCP port $port (an existing intro stack may be running)"
  else
    echo "ok: TCP port $port is available"
  fi
done

for dependency in tardigrade_ws tardigrade_unity_world; do
  if [[ -e "$intro_root/$dependency/.git" ]]; then
    echo "ok: $dependency submodule"
  else
    echo "missing: $dependency (run ./scripts/setup.sh)"
    failed=true
  fi
done

if submodule_status="$(git submodule status --recursive 2>/dev/null)"; then
  echo "Pinned revisions:"
  echo "$submodule_status"
  while IFS= read -r line; do
    case "${line:0:1}" in
      -)
        echo "missing: submodule is not initialized (run ./scripts/setup.sh)"
        failed=true
        ;;
      +)
        echo "mismatch: submodule is not at the revision pinned by this project"
        echo "Run ./scripts/setup.sh after saving any work inside submodules."
        failed=true
        ;;
      U)
        echo "conflict: submodule revision has unresolved merge conflicts"
        failed=true
        ;;
    esac
  done <<< "$submodule_status"
else
  echo "unable to inspect submodule revisions"
  failed=true
fi

if [[ "$(uname -m)" == "arm64" ]]; then
  echo "info: Apple Silicon will use linux/amd64 emulation for ROS Foxy"
fi

if command -v pnpm >/dev/null 2>&1 || command -v corepack >/dev/null 2>&1; then
  echo "ok: Foxglove extension build tooling"
else
  echo "optional: install Node.js/Corepack before the Foxglove milestone"
fi

unity_version_file="$intro_root/tardigrade_unity_world/ProjectSettings/ProjectVersion.txt"
if [[ -f "$unity_version_file" ]]; then
  echo "Unity requirement: $(sed -n 's/^m_EditorVersion: //p' "$unity_version_file")"
fi

echo "Disk availability:"
df -h "$intro_root" | tail -1

if [[ "$failed" == true ]]; then
  exit 1
fi
echo "Preflight passed."
