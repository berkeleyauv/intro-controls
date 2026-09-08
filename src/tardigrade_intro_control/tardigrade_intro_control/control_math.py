"""Pure control math shared by ROS nodes and unit tests."""

from dataclasses import dataclass
import math


def clamp(value, limit):
    return max(-limit, min(limit, value))


def wrap_angle(value):
    return math.atan2(math.sin(value), math.cos(value))


def world_error_to_body(error_x, error_y, yaw):
    """Rotate a planar error from odom coordinates into base_link."""
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    return (
        cosine * error_x + sine * error_y,
        -sine * error_x + cosine * error_y,
    )


@dataclass(frozen=True)
class PoseState:
    x: float
    y: float
    z: float
    yaw: float


@dataclass(frozen=True)
class ControllerGains:
    position_kp: float = 0.45
    depth_kp: float = 0.6
    yaw_kp: float = 0.8
    max_linear: float = 0.35
    max_vertical: float = 0.25
    max_yaw: float = 0.3
    position_tolerance: float = 0.12
    depth_tolerance: float = 0.08
    yaw_tolerance: float = 0.08


@dataclass(frozen=True)
class BodyCommand:
    forward: float = 0.0
    left: float = 0.0
    up: float = 0.0
    yaw: float = 0.0
    reached: bool = False


def compute_pose_command(current, target, gains=ControllerGains()):
    """Conservative proportional pose controller.

    This is a runnable baseline. Students should characterize it before adding
    derivative/integral terms, approach shaping, or disturbance rejection.
    """
    error_x = target.x - current.x
    error_y = target.y - current.y
    error_z = target.z - current.z
    yaw_error = wrap_angle(target.yaw - current.yaw)
    forward_error, left_error = world_error_to_body(
        error_x, error_y, current.yaw
    )
    reached = (
        math.hypot(error_x, error_y) <= gains.position_tolerance
        and abs(error_z) <= gains.depth_tolerance
        and abs(yaw_error) <= gains.yaw_tolerance
    )
    if reached:
        return BodyCommand(reached=True)
    return BodyCommand(
        forward=clamp(gains.position_kp * forward_error, gains.max_linear),
        left=clamp(gains.position_kp * left_error, gains.max_linear),
        up=clamp(gains.depth_kp * error_z, gains.max_vertical),
        yaw=clamp(gains.yaw_kp * yaw_error, gains.max_yaw),
        reached=False,
    )
