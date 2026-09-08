# Project Guide

## Goal

Use ROS 2 odometry and perception interfaces to stabilize the simulated AUV,
approach a gate, handle failures, and complete a short mission. The difficulty
should come from feedback, coordinate frames, latency, and recovery behavior—not
from reconstructing the repository setup.

## What is provided

- The production Tardigrade workspace as a pinned, read-only submodule.
- The production Unity simulator as a pinned, read-only submodule.
- A ROS 2 Python package that builds in the same workspace.
- Pure controller and mission-logic modules that can be unit tested without a
  running ROS graph.
- A conservative proportional pose-controller baseline.
- A weak procedural gate-mission baseline.
- Launch/config files and public tests.
- A versioned simulator interface contract.

## Milestones

### 1. ROS graph and baseline

- Build and launch the package.
- Start the ROS TCP endpoint and connect the pinned Unity simulator.
- Identify every topic type and coordinate frame used by the controller.
- Record a baseline response and explain it using plots.
- Confirm stale odometry and a missing enable heartbeat produce zero output.

### 2. Feedback control

- Improve the provided controller using measured results.
- Handle body-frame versus world-frame position error correctly.
- Wrap angular errors across `-pi` and `pi`.
- Respect command limits and avoid integral windup if integral action is added.
- Define and justify the goal-completion tolerance.

### 3. Gate approach

- Search when the gate is unavailable.
- Align before applying significant forward motion.
- Slow or stop as the desired stand-off distance is reached.
- Reject stale and low-confidence observations.
- Recover from temporary target loss.

### 4. Mission behavior

- Express search, alignment, approach, transit, and shutdown as a behavior tree
  using the staff-selected library.
- Add timeout and abort paths.
- Make cancellation or loss of healthy state command zero immediately.
- Complete randomized simulator scenarios.

The starter state machine in `mission_logic.py` defines useful behavior and
tests before the behavior-tree dependency is finalized. The final tree should
reuse controller functions rather than embed control math in tree nodes.

## Submission

Push to your assigned branch and open one draft pull request against `main`.
Include plots for at least two scenarios, final metrics, known failure cases,
and a short contribution summary.
