import math

from tardigrade_intro_control.control_math import (
    ControllerGains,
    PoseState,
    compute_pose_command,
    world_error_to_body,
    wrap_angle,
)


def test_wrap_angle_uses_shortest_direction():
    assert math.isclose(wrap_angle(2.0 * math.pi + 0.2), 0.2)


def test_world_error_rotates_into_body_frame():
    forward, left = world_error_to_body(1.0, 0.0, math.pi / 2.0)
    assert abs(forward) < 1e-9
    assert math.isclose(left, -1.0)


def test_controller_bounds_outputs():
    gains = ControllerGains(max_linear=0.2, max_vertical=0.1, max_yaw=0.15)
    command = compute_pose_command(
        PoseState(0.0, 0.0, 0.0, 0.0),
        PoseState(100.0, 100.0, 100.0, math.pi),
        gains,
    )
    assert abs(command.forward) <= 0.2
    assert abs(command.left) <= 0.2
    assert abs(command.up) <= 0.1
    assert abs(command.yaw) <= 0.15


def test_controller_commands_zero_at_goal():
    state = PoseState(1.0, 2.0, -1.0, 0.3)
    command = compute_pose_command(state, state)
    assert command.reached
    assert command.forward == command.left == command.up == command.yaw == 0.0
