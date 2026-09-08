# Berkeley AUV Controls Intro Project

Build and evaluate a feedback controller, then use it as part of a reactive
gate mission. The production ROS 2 workspace and Unity simulator are pinned as
Git submodules. Student code belongs in `src/tardigrade_intro_control/` and
runs against the same interfaces used by the production autonomy stack.

## Clone and set up

```bash
git clone --recurse-submodules https://github.com/berkeleyauv/intro-controls.git
cd intro_controls
./scripts/setup.sh
./docker-build.sh --build
```

Inside the container:

```bash
cd /ws
./build.sh
source install/setup.bash
ros2 launch tardigrade_intro_control pose_controller.launch.py
```

For the full visual simulation, open `tardigrade_unity_world/` with the Unity
Editor version in its `ProjectSettings/ProjectVersion.txt`. Start the ROS TCP
endpoint in the container, press **Play** in Unity, and then launch the student
controller:

```bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args \
  -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000
```

The simulator is active project infrastructure, not sample code: students use
its visual scene and ROS bridge while developing their controller. The current
pin applies commands and publishes odometry/status; simulated gate observations
and scenario controls are still being finalized against
`SIMULATOR_CONTRACT.md`. Update the pin once that work lands. Pinning a commit
keeps each project cohort reproducible even as later simulator work continues.

Run the public tests:

```bash
colcon test --packages-select tardigrade_intro_control
colcon test-result --verbose
```

Read [SIMULATOR_CONTRACT.md](SIMULATOR_CONTRACT.md) before writing control
code, then follow [GUIDE.md](GUIDE.md). The starter controller is intentionally
simple and is not suitable for the real vehicle.

## Repository boundaries

```text
tardigrade_ws/                  production ROS 2 packages; read-only
tardigrade_unity_world/         production Unity simulator; read-only
src/tardigrade_intro_control/   student-owned ROS 2 package
```

Students use both submodules actively but commit only to the outer intro
repository. Production-worthy work can be migrated later through a separate PR.

## Safety

This project is simulation-only. Its launch file does not arm the AUV or enable
external control. Never connect this package to powered hardware.
