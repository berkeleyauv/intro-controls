# Berkeley AUV Controls Intro Project

Build and evaluate a feedback controller, then use it as part of a reactive
gate mission. The production ROS 2 workspace is pinned as the `tardigrade_ws/`
Git submodule; student work belongs in `src/tardigrade_intro_control/`.

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

Run the public tests:

```bash
colcon test --packages-select tardigrade_intro_control
colcon test-result --verbose
```

Read [SIMULATOR_CONTRACT.md](SIMULATOR_CONTRACT.md) before writing control
code, then follow [GUIDE.md](GUIDE.md). The starter controller is intentionally
simple and is not suitable for the real vehicle.

## Safety

This project is simulation-only. Its launch file does not arm the AUV or enable
external control. Never connect this package to powered hardware.
