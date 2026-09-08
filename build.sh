#!/usr/bin/env bash
set -eo pipefail

intro_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$intro_root"

source /opt/ros/foxy/setup.bash
set -u
colcon build --symlink-install \
  --base-paths "$intro_root/src" "$intro_root/tardigrade_ws/src" \
  --packages-skip zed_components zed_wrapper zed_ros2
