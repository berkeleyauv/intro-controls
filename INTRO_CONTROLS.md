# Controls Intro Project

Your goal is to write a ROS 2 controller that commands the simulated Tardigrade
AUV to a requested pose, then use data from the simulator to decide whether the
controller is actually good. The simulator, state estimator, inner velocity
controller, thruster allocation, and visualization tools are provided. The
outer pose controller is yours.

Budget about two to three weeks. Commit at the end of each milestone. There is
no point rubric; checkoff is a working demonstration plus a conversation in
which you explain your design and evidence.

You are welcome to use AI tools. Treat generated code the same way you would
treat code sent to you by another teammate: read it, test it, and be ready to
explain or change it. A controller that moves in Unity but that nobody on the
team understands is not finished.

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
- write and package a ROS 2 Python node instead of only editing a provided
  callback;
- explain the `odom` and `base_link` frames, ENU/FLU axes, timestamps, and
  quaternions;
- implement the complete lifecycle of a cancelable, timeout-bounded
  `MoveToPose` action;
- turn pose error into bounded body-frame velocity setpoints;
- explain saturation, stale-data handling, settling, and the difference between
  the outer pose loop and inner velocity PID loop;
- use Foxglove and recorded data to compare controller tuning choices.

## What is provided and what is yours

The repository is split by ownership:

```text
src/tardigrade_intro_bringup/      provided launch and readiness tools
src/tardigrade_intro_interfaces/   provided MoveToPose action contract
src/tardigrade_intro_control/      your controller package
foxglove/                          provided starter layouts
tardigrade_ws/                     pinned production ROS workspace (read-only)
tardigrade_unity_world/            pinned Unity simulator (read-only)
```

At the start, `tardigrade_intro_control` is intentionally almost empty. It is a
valid ROS package, but it has no executable, controller, launch file,
configuration, or tests. You will add those pieces as you need them.

The command and feedback path will eventually be:

```text
your MoveToPose action server
  -> /tardigrade/control/velocity_setpoint/mission (TwistStamped, base_link)
  -> provided velocity mux
  -> provided six-axis velocity PID
  -> provided wrench allocator and actuator mapper
  -> /tardigrade/actuators/thruster_commands
  -> Unity plant
  -> simulated IMU + pressure + visual odometry
  -> provided EKF
  -> /tardigrade/state/odometry/filtered (Odometry, odom -> base_link)
```

Unity also publishes ground truth, but your controller must never subscribe to
it. Ground truth is useful for evaluation and visualization, not feedback.

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
pull, and pull request. The first three chapters of [Pro Git](https://git-scm.com/book/en/v2)
are a useful reference if any of those words are new.

## Milestone 1 — Docker and colcon

Start the pinned ROS Foxy development container. The first build is slow:

```bash
./dev.sh up --build
./dev.sh shell
```

An image contains the environment and installed dependencies. A container is a
running instance of that image. The project directory is mounted into the
container, so edits made on your host appear inside `/ws` and build output
appears back on your host. Docker's [images and containers overview](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)
has a longer explanation.

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
ros2 pkg executables tardigrade_intro_bringup
ros2 pkg executables tardigrade_intro_control
```

The last command should print nothing right now. Your package exists, but you
have not added an executable yet. That will change later.

Open more shells with `./dev.sh shell`; source the overlay in every shell after
rebuilding. `./dev.sh down` stops the container when you are finished. The ROS
2 [colcon tutorial](https://docs.ros.org/en/foxy/Tutorials/Colcon-Tutorial.html)
explains what the underlay and overlay workspaces are doing.

ROS Foxy is end-of-life, but this project intentionally pins Foxy to match the
robot. Follow the Foxy tutorial concepts while using the commands and APIs in
this container; do not silently replace the distribution.

## Milestone 2 — start Unity and the provided stack

Open `tardigrade_unity_world/` using the exact editor version printed by
preflight. Open `Assets/Scenes/SampleScene.unity`. In the ROS connection, select
ROS 2 with host `127.0.0.1` and TCP port `10000`. Leave Play mode stopped.

In a sourced container shell, start the provided infrastructure:

```bash
ros2 launch tardigrade_intro_bringup simulation.launch.py
```

A launch file starts a group of nodes with a repeatable configuration. This one
starts the ROS–TCP endpoint, state estimator, robot transforms, production
control chain, Rosbridge on port 9090, and a readiness monitor. It does not
start your future controller, press Play in Unity, arm the simulated plant, or
enable external control. The [ROS 2 launch tutorial](https://docs.ros.org/en/foxy/Tutorials/Launch-Files/Creating-Launch-Files.html)
shows what a smaller launch file looks like.

When the endpoint reports that it is listening on port 10000, press Play in
Unity. In a second sourced shell, run:

```bash
ros2 service call /tardigrade/intro/check_readiness std_srvs/srv/Trigger '{}'
ros2 topic echo /tardigrade/intro/readiness
```

Readiness should report live clock, status, and filtered odometry plus all three
simulator services. It deliberately does not require the vehicle to be armed.

If setup fails, inspect the graph before restarting everything:

```bash
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 topic hz /clock
ros2 topic hz /tardigrade/state/odometry/filtered
timeout 3 ros2 topic echo /tardigrade/status
```

Common causes are an unsourced shell, Unity not in Play mode, the wrong ROS
connection host or port, Docker not publishing ports 10000 and 9090, or a
second container already holding those ports.

## Milestone 3 — learn the live ROS graph

A ROS system is not one large program. It is a graph of nodes communicating
through typed interfaces. Read the Foxy introductions to
[nodes](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.html),
[topics](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html),
[services](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.html),
[parameters](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.html),
and [actions](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html).
Do not try to memorize every command. Use the tutorials to understand why each
communication type exists.

Work through the following on the running Tardigrade graph. Keep short notes
explaining what each command told you; screenshots alone are not an
explanation.

```bash
ros2 pkg list | grep tardigrade
ros2 node info /readiness_monitor
ros2 topic info --verbose /tardigrade/state/odometry/filtered
ros2 topic info --verbose /tardigrade/control/velocity_setpoint/mission
ros2 interface show nav_msgs/msg/Odometry
ros2 interface show geometry_msgs/msg/TwistStamped
ros2 interface show tardigrade_interfaces/msg/RobotStatus
ros2 interface show tardigrade_interfaces/srv/SetArmed
ros2 interface show tardigrade_intro_interfaces/action/MoveToPose
ros2 action list -t
ros2 param list /velocity_wrench_controller
ros2 param get /velocity_wrench_controller surge.kp
```

Answer these before writing the controller:

1. Which node publishes filtered odometry?
2. Which node is the final owner of the thruster-command topic?
3. Why is odometry a topic, arming a service, and move-to-pose an action?
4. What do positive X, Y, Z, and yaw mean in `odom` and `base_link`?
5. Why will your command use `TwistStamped` instead of `Twist`?
6. What should your controller do if odometry stops arriving?
7. What part of the stack turns a desired velocity into thruster effort?

You will use ENU world coordinates and an FLU body frame. Read
[REP 103](https://www.ros.org/reps/rep-0103.html) for axis conventions and
[REP 105](https://www.ros.org/reps/rep-0105.html) for the meaning of common
mobile-robot frames. Draw the two frames and one example in your notes: if the
vehicle faces positive world Y and the target lies at positive world X, which
body direction should it command?

## Milestone 4 — write your first node

The package skeleton lives in `src/tardigrade_intro_control/`. Read the Foxy
[Python publisher/subscriber tutorials](https://docs.ros.org/en/foxy/Tutorials/Beginner-Client-Libraries.html),
then add an executable node named `move_to_pose_server` to the package. You will
grow this same node through the rest of the project; do not make a throwaway
talker/listener package.

For this milestone, the node only needs to:

- subscribe to `/tardigrade/state/odometry/filtered` as `nav_msgs/msg/Odometry`;
- use a sensor-data QoS profile suitable for streamed measurements;
- print the current position and yaw at a reasonable rate, not once per
  high-rate message;
- publish a neutral `geometry_msgs/msg/TwistStamped` on
  `/tardigrade/control/velocity_setpoint/mission` from a timer;
- stamp each command and set `header.frame_id` to `base_link`;
- expose the odometry and command topic names as parameters.

You will need to edit `setup.py` to register the executable. Rebuild, source,
and verify it using both `ros2 run` and graph inspection:

```bash
./build.sh
source install/setup.bash
ros2 pkg executables tardigrade_intro_control
ros2 run tardigrade_intro_control move_to_pose_server
```

Use `ros2 node info` and `ros2 topic echo` to prove that the node has the
connections and message fields you intended. The vehicle should not move
because every command is neutral.

This is also where QoS becomes real. A subscriber and publisher can have the
same topic name and message type but still fail to communicate if their QoS
policies are incompatible. Read the Foxy [QoS overview](https://docs.ros.org/en/foxy/Concepts/About-Quality-of-Service-Settings.html)
and write down why you selected your odometry subscription profile.

Commit this milestone before turning the neutral publisher into a controller.

## Milestone 5 — implement and test the outer controller

Keep the control math separate from ROS callbacks so that it can be tested with
plain Python values. You choose the exact classes and function names. At a
minimum, the math must:

- validate and normalize an input quaternion before extracting yaw;
- compute the shortest signed yaw error across `-pi` and `pi`;
- rotate planar position error from `odom` into the current `base_link` frame;
- produce proportional forward, left, up, and yaw-rate commands;
- clamp each command to a configurable symmetric limit;
- report whether planar position, depth, and yaw are all within their separate
  tolerances;
- reject non-finite inputs instead of publishing them.

The outer controller requests body velocities. It does not calculate individual
thruster forces and it does not replace the provided velocity PID. A useful
starting law is

```text
world position error -> rotate into body frame -> multiply by Kp -> clamp
shortest yaw error   -> multiply by Kp              -> clamp
```

Do the frame derivation yourself before asking an agent to write it. Test a
vehicle at yaw `pi/2`; that case catches many sign mistakes. The ROS 2
[quaternion fundamentals tutorial](https://docs.ros.org/en/foxy/Tutorials/Tf2/Quaternion-Fundamentals.html)
is useful background, although this project controls only yaw.

Create unit tests under `src/tardigrade_intro_control/test/`. Include at least:

- zero error produces a neutral, reached result;
- a 90-degree heading rotates world X error into the correct body axis;
- yaw takes the short way across the wrap boundary;
- every output respects its limit for a very large error;
- a scaled but valid quaternion is normalized;
- a zero or non-finite quaternion is rejected;
- being close in position but outside yaw tolerance is not reached.

Run the tests inside the container:

```bash
colcon test --packages-select tardigrade_intro_control
colcon test-result --verbose
```

Do not tune gains by editing Python constants. In the next milestone, gains and
limits will come from ROS parameters.

## Milestone 6 — build the complete `MoveToPose` action

An action represents a task that takes time, produces feedback, returns a
result, and can be canceled. Revisit the
[actions tutorial](https://docs.ros.org/en/foxy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.html)
and read the Python action server/client tutorial linked from the Foxy client
library tutorials. Inspect the provided contract:

```bash
ros2 interface show tardigrade_intro_interfaces/action/MoveToPose
```

Turn your node into the complete action server. Its public behavior is the
specification; the internal design is yours.

### Goal handling

- The action name is `/tardigrade/intro/move_to_pose`.
- Accept only targets whose `header.frame_id` is `odom`.
- Reject non-finite positions, invalid quaternions, and non-positive timeouts.
- Accept only one active goal.
- Require fresh odometry and a connected, armed, external-control-enabled
  simulator before accepting a goal.

### Control and feedback

- Subscribe to `/tardigrade/status` as `tardigrade_interfaces/msg/RobotStatus`.
- Run control from a timer at a configurable rate; do not publish commands from
  the odometry callback.
- Publish bounded `TwistStamped` commands in `base_link`.
- Publish action feedback containing current position, position error, yaw
  error, and a useful controller state.
- Declare gains, limits, tolerances, control rate, feedback rate, odometry
  timeout, and settle time as ROS parameters.
- Put their default values in a YAML file rather than scattering constants
  through the node.

### Completion and failure

- Succeed only after every tolerance remains satisfied for the full settle
  time.
- On cancellation, stop the goal and immediately publish a neutral command.
- Abort on goal timeout, stale odometry, or loss of either safety gate.
- Publish a neutral command whenever a goal ends for any reason and during node
  shutdown.
- Never let state from one goal affect the next goal.

Use a monotonic clock for wall-time watchdogs and the action timeout. Use the
ROS clock for message stamps. Simulation time can pause or jump; elapsed safety
checks should not accidentally become immortal when that happens.

Add a launch file named `controller.launch.py` and a controller YAML file to
your package. Update `setup.py` so both are installed. Your normal workflow
should now be:

```bash
ros2 launch tardigrade_intro_bringup simulation.launch.py
ros2 launch tardigrade_intro_control controller.launch.py
```

The first command is infrastructure we maintain for you. The second command is
part of your submission and should be understandable to you.

## Milestone 7 — integrate with Unity and try to break it

Reset starts a deterministic scenario and turns both safety gates off:

```bash
ros2 service call /tardigrade/sim/reset \
  tardigrade_interfaces/srv/ResetSimulation \
  "{scenario_id: clean, seed: 42, initial_pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}"
```

Read the status, then explicitly enable external control and arm:

```bash
ros2 service call /tardigrade/set_external_control \
  tardigrade_interfaces/srv/SetExternalControl '{enabled: true}'
ros2 service call /tardigrade/set_armed \
  tardigrade_interfaces/srv/SetArmed '{armed: true}'
```

Send a target with nonzero X, Y, depth, and yaw. The quaternion below is yaw =
0.5 rad:

```bash
ros2 action send_goal /tardigrade/intro/move_to_pose \
  tardigrade_intro_interfaces/action/MoveToPose \
  "{target: {header: {frame_id: odom}, pose: {position: {x: 3.0, y: 1.0, z: -1.0}, orientation: {z: 0.247404, w: 0.968912}}}, timeout: {sec: 30}}" \
  --feedback
```

Do not stop after the first successful motion. Run and record this fault matrix:

| Test | Required result |
|---|---|
| target in the wrong frame | goal rejected |
| second target while one is active | one clear rejection, no mixed state |
| cancel during motion | canceled result and neutral command |
| stop the controller during motion | neutral command during shutdown |
| pause or disconnect the odometry source | abort after watchdog and go neutral |
| disable external control during motion | abort and go neutral |
| target yaw across `-pi`/`pi` | take the short direction |
| valid target | remain in tolerance, then succeed |

Some of these tests may expose a race rather than a math error. That is part of
the project. Add a regression test for at least one bug you find here.

At the end of every run, disarm before stopping Unity:

```bash
ros2 service call /tardigrade/set_armed \
  tardigrade_interfaces/srv/SetArmed '{armed: false}'
```

Explain why arming and external control are services rather than persistent
Boolean topics, and why the provided launch file does not call them for you.

## Milestone 8 — Foxglove, rosbag, and controller evidence

Foxglove lets you see the live graph, while rosbag lets you replay the exact
messages from an experiment. Read the ROS 2 tutorial on
[recording and playing back data](https://docs.ros.org/en/foxy/Tutorials/Ros2bag/Recording-And-Playing-Back-Data.html)
before recording your first run.

Install Foxglove Desktop. The production workspace contains the team's Vehicle
Status, Attitude, and PID Tuner extension. Build it on the host once:

```bash
./scripts/build-foxglove-extension.sh
```

Install the generated `.foxe` file from
`tardigrade_ws/foxglove/extensions/tardigrade-tools/`. If local extensions are
unavailable, import `foxglove/intro_controls_builtin.json`; the built-in layout
still supports the required plotting work.

Add a **Rosbridge** connection to `ws://localhost:9090`. Import the intro layout
and plot at least target/current position, yaw error, commanded velocity, the
chosen inner-loop PID debug topic, and thruster commands.

The inner velocity controller publishes
`/tardigrade/control/{surge,sway,heave,roll,pitch,yaw}/debug`. Choose one axis
and compare three bounded runs:

- clearly under-responsive;
- deliberately aggressive but still safe;
- your best justified tuning.

Keep the target, clean scenario, seed, and initial pose fixed. Record the
filtered odometry, action feedback, mission command, selected PID debug topic,
controller enabled state, and thruster commands. Use `ros2 bag info` afterward
to verify what the bag actually contains.

Write a small analysis script for your recorded data or a CSV exported from the
plots. Report rise time, overshoot, settling time, final error, and the fraction
of samples that were saturated. Graphs are evidence; a screenshot followed by
"this one looks best" is not an analysis.

Be ready to explain:

- why the outer pose loop and inner velocity loop are separate;
- what increasing P changed;
- what saturation looked like in the data;
- whether noise or delay limited your tuning;
- why your chosen run is preferable to the other two.

## Milestone 9 — final demonstration and checkoff

Demonstrate from a clean reset and recorded seed:

1. start the container, build, and source without help;
2. start Unity and the provided simulation launch;
3. prove readiness by inspecting the ROS graph;
4. start your controller using your launch file and YAML configuration;
5. open the Foxglove layout;
6. reset, explicitly enable external control, and arm;
7. send a target with nonzero X, Y, depth, and yaw;
8. show action feedback, PID debug, actuator commands, and Unity motion;
9. cancel one goal and show the neutral command;
10. complete one goal and show settled success;
11. demonstrate one stale-data or safety-gate failure;
12. disarm and shut down safely.

During checkoff, expect to explain a section of your code and make a small
change. This is not meant to catch you out; it verifies that the code belongs
to the team members submitting it rather than only to an AI session.

Open a draft pull request containing meaningful commits, your tests, a short
architecture/frame explanation, the completed fault matrix, tuning evidence
from the three comparable runs, your analysis script, the final Unity video,
known limitations, and each contributor's work. Do not commit bags, build
output, the packaged Foxglove extension, or edits in the two production
submodules.

## Troubleshooting map

| Symptom | Inspect first |
|---|---|
| Intro packages not found | source `install/setup.bash`, then run `colcon list` |
| Your executable is missing | `setup.py` entry point, rebuild, source again |
| Unity says connection refused | endpoint log, port 10000, ROS 2 mode |
| Readiness lacks odometry | Unity Play mode, `/clock`, raw VIO/IMU, EKF logs |
| Goal is always rejected | odometry freshness and simulator status fields |
| Mission topic changes but wrench is zero | command freshness and velocity mux source |
| Thruster commands change but body is still | Unity armed/external-control status |
| Goal never succeeds near target | individual tolerances and settle-time reset logic |
| Foxglove is empty | Rosbridge connection type, port, and selected layout |
| Tests pass but Unity moves incorrectly | frame rotation, sign convention, and timestamps |

The pinned production documentation under
`tardigrade_ws/docs/unity_operator_workflow.md` and
`tardigrade_ws/docs/unity_sil.md` is useful deeper reference. This file remains
the authoritative sequence and submission contract for the intro project.
