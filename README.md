# Berkeley AUV Controls Intro

This is the simulation-only onboarding project for Berkeley AUV controls. You
will bring up the real Tardigrade Unity/ROS 2 stack, learn to inspect its ROS
graph, write a `MoveToPose` controller and action server, and investigate an
inner velocity PID loop using recorded data.

Start with [INTRO_CONTROLS.md](INTRO_CONTROLS.md). It is the single project
guide and contains setup, milestones, commands, safety rules, and the final
checkoff expectations.

The provided simulation launch lives in `src/tardigrade_intro_bringup/`. Student
controller work belongs in `src/tardigrade_intro_control/`. Treat
`src/tardigrade_intro_interfaces/`, `tardigrade_ws/`, and
`tardigrade_unity_world/` as provided contracts and infrastructure.
