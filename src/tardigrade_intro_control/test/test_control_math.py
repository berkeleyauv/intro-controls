import math

from tardigrade_intro_control.control_math import (
    ControllerGains,
    PoseState,
    compute_pose_command,
    world_error_to_body,
    wrap_angle,
    yaw_from_quaternion,
)


def test_wrap_angle_uses_shortest_direction():
    assert math.isclose(wrap_angle(2.0 * math.pi + 0.2), 0.2)


def test_world_error_rotates_into_body_frame():
    forward, left = world_error_to_body(1.0, 0.0, math.pi / 2.0)
    assert abs(forward) < 1e-9
    assert math.isclose(left, -1.0)


def test_quaternion_is_normalized_before_yaw_conversion():
    yaw = yaw_from_quaternion(
        0.0,
        0.0,
        2.0 * math.sin(0.25),
        2.0 * math.cos(0.25),
    )
    assert math.isclose(yaw, 0.5)


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


def test_starter_is_intentionally_incomplete_off_x_axis():
    command = compute_pose_command(
        PoseState(0.0, 0.0, 0.0, 0.0),
        PoseState(0.0, 1.0, -1.0, 0.5),
    )
    assert not command.reached
    assert command.forward == 0.0
    assert command.left == command.up == command.yaw == 0.0
