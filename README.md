# Berkeley AUV Controls Intro

This is the simulation-only onboarding project for Berkeley AUV controls. You
will bring up the real Tardigrade Unity/ROS 2 stack, learn to inspect and use a
ROS graph, implement a `MoveToPose` action server, and investigate a velocity
PID loop in Foxglove.

Start with [INTRO_CONTROLS.md](INTRO_CONTROLS.md). It is the single project
guide and contains setup, milestones, commands, safety rules, and the final
checkoff expectations.

The two pinned submodules are reference infrastructure. Make project changes in
`src/tardigrade_intro_control/` and `src/tardigrade_intro_interfaces/`, not in
`tardigrade_ws/` or `tardigrade_unity_world/`.
