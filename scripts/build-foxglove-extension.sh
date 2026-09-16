#!/usr/bin/env bash
set -euo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
extension_root="$intro_root/tardigrade_ws/foxglove/extensions/tardigrade-tools"

if [[ ! -f "$extension_root/package.json" ]]; then
  echo "Missing pinned Foxglove extension. Run ./scripts/setup.sh first."
  exit 1
fi

if command -v pnpm >/dev/null 2>&1; then
  package_manager=(pnpm)
elif command -v corepack >/dev/null 2>&1; then
  package_manager=(corepack pnpm)
else
  echo "pnpm is required. Install Node.js with Corepack, then retry."
  exit 1
fi

cd "$extension_root"
"${package_manager[@]}" install --frozen-lockfile
"${package_manager[@]}" run typecheck
"${package_manager[@]}" run package

echo "Built extension:"
find "$extension_root" -maxdepth 1 -name '*.foxe' -print
