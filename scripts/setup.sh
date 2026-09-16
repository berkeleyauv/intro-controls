#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$intro_root"
git submodule update --init --recursive

echo "Submodules initialized at the revisions pinned by this project."
echo "Next run: ./scripts/preflight.sh"
