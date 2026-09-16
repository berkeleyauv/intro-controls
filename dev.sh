#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
compose_root="$intro_root/tardigrade_ws"
container_name="${NAME:-tardigrade-intro-controls}"

if [[ ! -f "$compose_root/docker/compose.yaml" ]]; then
  echo "Missing tardigrade_ws. Run ./scripts/setup.sh first."
  exit 1
fi

if [[ "$(uname -m)" == "arm64" && -z "${DOCKER_DEFAULT_PLATFORM:-}" ]]; then
  export DOCKER_DEFAULT_PLATFORM=linux/amd64
fi

export WORKSPACE="$intro_root"
export NAME="$container_name"

compose() {
  (cd "$compose_root" && docker compose -f docker/compose.yaml "$@")
}

usage() {
  cat <<'EOF'
Usage: ./dev.sh COMMAND [options]

Commands:
  up [--build]  Start the ROS development container in the background.
  shell         Open an interactive, automatically sourced shell.
  build         Build the workspace inside the running container.
  logs          Follow container logs.
  status        Show container status.
  down          Stop and remove the development container.
EOF
}

command="${1:-}"
if [[ -n "$command" ]]; then
  shift
fi

case "$command" in
  up)
    build=false
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --build) build=true ;;
        *) echo "Unknown up option: $1"; usage; exit 1 ;;
      esac
      shift
    done
    if [[ "$build" == true ]]; then
      compose build
    fi
    compose up -d
    echo "Container ready. Enter it with: ./dev.sh shell"
    ;;
  shell)
    compose exec tardigrade bash
    ;;
  build)
    compose exec tardigrade bash -lc 'cd /ws && ./build.sh'
    ;;
  logs)
    compose logs -f tardigrade
    ;;
  status)
    compose ps
    ;;
  down)
    compose down
    ;;
  -h|--help|help|'')
    usage
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
