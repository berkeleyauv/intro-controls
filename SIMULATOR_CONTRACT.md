# Simulator Contract

Status: **draft v0.1**. Freeze this document before the project is distributed.

The simulator may change internally, but student code depends only on these
robot-level ROS interfaces.

## Inputs to the simulator

```text
/tardigrade/cmd_vel                   geometry_msgs/Twist
/tardigrade/set_armed                 tardigrade_interfaces/SetArmed
/tardigrade/set_external_control      tardigrade_interfaces/SetExternalControl
```

For the intro project, each `Twist` component is a normalized body command in
`[-1, 1]`. Positive linear X is forward, positive linear Y is left, positive
linear Z is up, and angular signs follow the right-hand rule. The simulator
maps this command through its dynamics; student code must not assume it is an
instantaneous physical velocity.

## Outputs from the simulator

```text
/tardigrade/state/odometry            nav_msgs/Odometry
/tardigrade/perception/gate           tardigrade_interfaces/GateDetection
/tardigrade/status                    tardigrade_interfaces/RobotStatus
```

Odometry reports `odom -> base_link`. Gate yaw error is positive when the gate
is robot-left. Timestamps determine freshness; receipt alone is insufficient.

## Required scenario controls

The final simulator harness should expose:

- A deterministic random seed.
- Initial vehicle pose.
- Gate pose.
- Constant current or disturbance magnitude.
- Measurement noise and latency.
- Reset without restarting the entire development environment.

## Safety behavior

- No launch file arms automatically.
- Motion requires explicit simulated arming and external-control enable.
- Stale commands become zero.
- Stale odometry or perception causes student autonomy to command zero.
