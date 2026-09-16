# Controls Intro Project

Your goal is to command the simulated Tardigrade AUV to a requested pose and
watch the complete control chain operate in Unity. The assignment is a thin
student overlay on pinned versions of the real ROS 2 workspace and Unity world.
You will use the same messages, estimator, PID controller, allocator, safety
services, and Foxglove tools as the main project without making onboarding
changes directly in production code.

Budget about two to three weeks. Commit at the end of each milestone. There is
no point rubric; checkoff is a working demonstration plus a conversation in
which you explain your design and evidence.

> **Simulation only.** Never run this package against a powered vehicle. No
> provided command automatically arms or enables external control.

## What you will learn

By the end, you should be able to:

- clone submodules, work on a feature branch, make useful commits, and open a
  draft pull request;
- build and source a colcon workspace in Docker and explain why both steps are
  necessary;
- inspect ROS 2 packages, nodes, topics, message types, services, actions,
  parameters, launch files, QoS, and bag recordings;
- explain the `odom` and `base_link` frames, ENU/FLU axes, timestamps, and
  quaternions;
- implement the lifecycle of a cancelable, timeout-bounded `MoveToPose` action;
- turn pose error into bounded body-frame velocity setpoints;
- explain P, I, and D terms, saturation, integral windup, derivative filtering,
  and the difference between the outer pose loop and inner velocity loop;
- use Foxglove and rosbag data to compare controller tuning choices.

## Architecture and ownership

The repository is deliberately split by ownership:

```text
src/tardigrade_intro_interfaces/   the assignment's MoveToPose action
src/tardigrade_intro_control/      your node, control math, config, and tests
foxglove/                          assignment-specific layout
tardigrade_ws/                     pinned production ROS workspace (read-only)
tardigrade_unity_world/            pinned Unity simulator (read-only)
```

The command and feedback path is:

```text
your MoveToPose action
  -> /tardigrade/control/velocity_setpoint/mission (TwistStamped, base_link)
  -> production velocity mux
  -> six-axis velocity PID and PidDebug topics
  -> wrench allocator and actuator mapper
  -> /tardigrade/actuators/thruster_commands
  -> Unity plant
  -> IMU + pressure + visual odometry
  -> EKF
  -> /tardigrade/state/odometry/filtered (Odometry, odom -> base_link)
```

Unity also publishes ground truth, but your controller must never subscribe to
it. Ground truth is only for simulator evaluation and visualization.

## Milestone 0 — clone, branch, and preflight

Install Git, Docker Desktop or OrbStack, Unity Hub, and Foxglove Desktop. Clone
with submodules and create your own branch:

```bash
git clone --recurse-submodules https://github.com/berkeleyauv/intro-controls.git
cd intro-controls
git switch -c <your-name>/controls-intro
./scripts/preflight.sh
```

If you already cloned without submodules, run `./scripts/setup.sh`. Preflight
prints the exact Unity editor version from the pinned project; install that
version in Unity Hub. Do not upgrade the project when Unity prompts you.

Notice that `git status` does not include ROS build products or Unity's local
asset churn. Before every commit, still read the complete diff:

```bash
git status --short
git diff
```

Be ready to explain the difference between a clone, submodule, branch, commit,
pull, and pull request.

## Milestone 1 — Docker and colcon

Start the pinned ROS Foxy development container. The first build is slow:

```bash
./dev.sh up --build
./dev.sh shell
```

Inside the container, build and source the overlay:

```bash
./build.sh
source install/setup.bash
```

`colcon build` creates `build/`, `install/`, and `log/`. Sourcing
`install/setup.bash` makes the newly built packages and interfaces discoverable
in that shell. Verify both concepts instead of treating the commands as magic:

```bash
colcon list | grep tardigrade_intro
ros2 pkg prefix tardigrade_intro_control
ros2 interface show tardigrade_intro_interfaces/action/MoveToPose
ros2 pkg executables tardigrade_intro_control
```

Run the tests whenever you change controller math:

```bash
colcon test --packages-select tardigrade_intro_control
colcon test-result --verbose
```

Open more shells with `./dev.sh shell`; source the overlay in every shell after
rebuilding. `./dev.sh down` stops the container when you are finished.

ROS Foxy is end-of-life, but this project intentionally pins Foxy to match the
robot. Follow the Foxy tutorial concepts while using the commands and APIs in
this container; do not silently replace the distribution.

## Milestone 2 — start Unity and expose the ROS graph

Open `tardigrade_unity_world/` using the exact editor version printed by
preflight. Open `Assets/Scenes/SampleScene.unity`. In the ROS connection, select
ROS 2 with host `127.0.0.1` and TCP port `10000`. Leave Play mode stopped.

In a sourced container shell, start the infrastructure:

```bash
ros2 launch tardigrade_intro_control infrastructure.launch.py
```

This one launch starts the ROS–TCP endpoint, estimator, robot transforms,
production control chain with the `mission` source selected, Rosbridge on port
9090, and a readiness monitor. It does **not** start Unity, your action server,
a mission, arming, or external control.

When the endpoint reports that it is listening on port 10000, press Play in
Unity. The authored scene should contain the pool, gate, Tardigrade body, and
stereo cameras. Unity safely begins disarmed and retries if ROS was not ready.

In a second sourced shell, run:

```bash
ros2 service call /tardigrade/intro/check_readiness std_srvs/srv/Trigger '{}'
ros2 topic echo /tardigrade/intro/readiness
```

Readiness should report live clock, status, and filtered odometry plus all three
simulator services. It deliberately does not require the plant to be armed.

If setup fails, inspect rather than restart everything blindly:

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 topic hz /clock
ros2 topic hz /tardigrade/state/odometry/filtered
timeout 3 ros2 topic echo /tardigrade/status
```

Common causes are an unsourced shell, Unity not in Play mode, the wrong ROS
connection host/port, Docker not publishing ports 10000 and 9090, or a second
container already holding those ports.

## Milestone 3 — learn the live ROS graph

Work through these on the running Tardigrade graph. Keep short notes explaining
what each command told you; command screenshots alone are not an explanation.

```bash
ros2 pkg list | grep tardigrade
ros2 pkg executables tardigrade_intro_control
ros2 node info /readiness_monitor
ros2 topic info --verbose /tardigrade/state/odometry/filtered
ros2 interface show nav_msgs/msg/Odometry
ros2 interface show geometry_msgs/msg/TwistStamped
ros2 interface show tardigrade_interfaces/srv/SetArmed
ros2 action list -t
ros2 param list /velocity_wrench_controller
ros2 param get /velocity_wrench_controller surge.kp
```

Answer these during checkoff:

1. Why is odometry a topic, reset a service, and move-to-pose an action?
2. Which node is the only owner of the final thruster-command topic?
3. What do positive X, Y, Z, and yaw mean in `odom` and `base_link`?
4. Why does the command use `TwistStamped` instead of an unstamped `Twist`?
5. What should happen if odometry or a command becomes stale?
6. What QoS reliability and queue depth do your subscriptions use, and why?

Record and inspect a short bag before controlling anything:

```bash
mkdir -p bags
ros2 bag record -o bags/setup-check \
  /clock /tardigrade/status /tardigrade/state/odometry/filtered
ros2 bag info bags/setup-check
```

Bag directories are ignored by Git. Stop recording with Ctrl-C.

## Milestone 4 — services and explicit safety gates

Reset to a deterministic clean scenario:

```bash
ros2 service call /tardigrade/sim/reset \
  tardigrade_interfaces/srv/ResetSimulation \
  "{scenario_id: clean, seed: 42, initial_pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}"
```

Reset turns both safety gates off. Read the status, then explicitly enable
external control and arm the simulated plant:

```bash
ros2 service call /tardigrade/set_external_control \
  tardigrade_interfaces/srv/SetExternalControl '{enabled: true}'
ros2 service call /tardigrade/set_armed \
  tardigrade_interfaces/srv/SetArmed '{armed: true}'
```

At the end of every run, disarm before stopping nodes or Unity:

```bash
ros2 service call /tardigrade/set_armed \
  tardigrade_interfaces/srv/SetArmed '{armed: false}'
```

Explain why these are services rather than persistent Boolean topics and why
the setup launch does not call them for you.

## Milestone 5 — implement `MoveToPose`

Build and run the starter action server in another sourced shell:

```bash
ros2 launch tardigrade_intro_control controller.launch.py
ros2 action info /tardigrade/intro/move_to_pose
```

Send a 30-second goal from another shell. The quaternion below is yaw = 0.5
rad; pose positions use metres in ENU `odom`:

```bash
ros2 action send_goal /tardigrade/intro/move_to_pose \
  tardigrade_intro_interfaces/action/MoveToPose \
  "{target: {header: {frame_id: odom}, pose: {position: {x: 3.0, y: 1.0, z: -1.0}, orientation: {z: 0.247404, w: 0.968912}}}, timeout: {sec: 30}}" \
  --feedback
```

While a goal is running, press Ctrl-C in that client terminal to request
cancellation and watch the server publish a neutral command.

The starter is intentionally incomplete: it demonstrates the full action
lifecycle but commands only odometry-X surge. It cannot reach the supplied
target. Complete the TODOs in `control_math.py` and `pid.py`, and add tests
before changing the ROS wrapper. Your finished controller must:

- rotate planar error from `odom` into the current `base_link` frame;
- command bounded forward, left, up, and yaw-rate setpoints;
- take the shortest yaw path across `-pi`/`pi`;
- report useful action feedback while running;
- succeed only after every tolerance remains satisfied for the configured
  settle time;
- accept cancellation and publish a neutral command;
- abort on goal timeout, missing/stale odometry, or invalid input;
- reset controller history between goals and never reuse an old integral;
- allow only one active goal.

The node already handles action transport, timeout, cancellation, stale-input
abort, and neutral-command cleanup. Read and explain that code, then improve
the pure controller rather than bypassing its safety behavior.

Use P control for planar position and depth. For yaw, implement and test a real
PID update with elapsed `dt`, an integral limit, output saturation,
anti-windup, derivative-on-measurement or a filtered derivative, and reset.
The yaw PID outputs a desired yaw rate; the production velocity PID is the
inner loop that turns that rate request into torque.

Do not tune by changing constants in Python. Use
`src/tardigrade_intro_control/config/controller.yaml` and ROS parameters.

## Milestone 6 — Foxglove and PID investigation

Install Foxglove Desktop. The production workspace already contains the team's
original Vehicle Status, Attitude, and PID Tuner extension. Build it on the
host once:

```bash
./scripts/build-foxglove-extension.sh
```

In Foxglove Desktop, install this generated local extension:

```text
tardigrade_ws/foxglove/extensions/tardigrade-tools/berkeleyauv.tardigrade-tools-0.1.0.foxe
```

Foxglove currently requires a developer-enabled account to install a local
extension. If that is unavailable, import
`foxglove/intro_controls_builtin.json`; it uses only built-in panels and keeps
the required topic/plotting work, though it omits the team's custom controls.

Add a **Rosbridge** connection to `ws://localhost:9090` (not a Foxglove
WebSocket connection). Import `foxglove/intro_controls.json`. The full
assignment layout reuses the production PID Tuner, Vehicle Status, and Attitude
panels and adds plots for action position/yaw error.

The inner velocity controller publishes
`/tardigrade/control/{surge,sway,heave,roll,pitch,yaw}/debug`. Select one axis
at a time in PID Tuner. It calls
`/tardigrade/control/set_velocity_pid_gains` atomically and can reset controller
history through `/tardigrade/control/reset_pid`. Live service changes are
temporary and reset PID history; they do not alter the pinned production YAML.

For one axis, record and compare three bounded runs:

- P-only or clearly under-responsive;
- deliberately aggressive but still safe/saturated;
- your best justified tuning.

Keep the target, clean scenario, seed, and initial pose fixed. Record the debug
topic, filtered odometry, action feedback, controller enabled state, and
thruster commands. Explain rise time, overshoot, settling, steady-state error,
noise, saturation, and what each P/I/D contribution did. Do not choose gains
only because one run looked good.

You can also call the tuning service from the CLI:

```bash
ros2 service call /tardigrade/control/set_velocity_pid_gains \
  tardigrade_interfaces/srv/SetVelocityPidGains \
  '{axis: surge, kp: 45.0, ki: 3.0, kd: 3.0, integral_limit: 20.0, output_limit: 80.0}'
```

## Milestone 7 — final demonstration and checkoff

Demonstrate from a clean reset and a recorded seed:

1. start the container, build, and source without help;
2. start Unity and the infrastructure launch;
3. prove readiness from the ROS graph;
4. open the intro Foxglove layout;
5. reset, explicitly enable external control, and arm;
6. send a target with nonzero X, Y, depth, and yaw;
7. show action feedback, PID debug, actuator commands, and Unity motion;
8. cancel one goal and show a neutral command;
9. complete one goal and show the final error and settled success;
10. disarm and shut down safely.

Open a draft pull request containing meaningful commits, your tests, a short
architecture/frame explanation, tuning evidence from the three comparable
runs, the final Unity video, known limitations, and each contributor's work.
Do not commit bags, build output, the packaged Foxglove extension, or edits in
the two production submodules.

## Troubleshooting map

| Symptom | Inspect first |
|---|---|
| Intro packages not found | `source install/setup.bash`, then `colcon list` |
| Unity says connection refused | endpoint log, port 10000, ROS 2 mode |
| Readiness lacks odometry | Unity Play mode, `/clock`, raw VIO/IMU, EKF logs |
| Goal accepted but no motion | status safety gates, mission topic, mux parameter |
| Mission topic changes but wrench is zero | command/odometry freshness topics |
| Thruster command changes but body is still | Unity armed/external status |
| Foxglove is empty | Rosbridge connection type/port and selected layout |
| PID panel missing | build/install the pinned `tardigrade-tools` extension |
| Goal aborts while debugging | odometry watchdog or requested action timeout |

The pinned production simulator documentation under
`tardigrade_ws/docs/unity_operator_workflow.md` and
`tardigrade_ws/docs/unity_sil.md` is useful deeper reference, but this file is
the authoritative sequence for the intro project.
