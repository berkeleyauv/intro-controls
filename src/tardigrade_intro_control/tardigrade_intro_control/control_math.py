"""Pure control math shared by ROS nodes and unit tests."""

from dataclasses import dataclass
import math


def clamp(value, limit):
    return max(-limit, min(limit, value))


def wrap_angle(value):
    return math.atan2(math.sin(value), math.cos(value))


def yaw_from_quaternion(x, y, z, w):
    """Return yaw after validating and normalizing quaternion components."""
    values = (x, y, z, w)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("quaternion values must be finite")
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-9:
        raise ValueError("quaternion must be non-zero")
    x, y, z, w = (value / norm for value in values)
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


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
    """Intentionally weak, runnable controller baseline.

    It only handles motion along the odometry X axis. That proves the ROS and
    simulator plumbing, but cannot reach the project target. Students extend
    this pure function to control body-frame forward/left, depth, and yaw while
    preserving the safety limits below. The ROS wrapper owns action lifecycle
    and watchdog behavior; keep that separation when completing the project.
    """
    error_x = target.x - current.x
    error_y = target.y - current.y
    error_z = target.z - current.z
    yaw_error = wrap_angle(target.yaw - current.yaw)
    reached = (
        math.hypot(error_x, error_y) <= gains.position_tolerance
        and abs(error_z) <= gains.depth_tolerance
        and abs(yaw_error) <= gains.yaw_tolerance
    )
    if reached:
        return BodyCommand(reached=True)
    return BodyCommand(
        # TODO(project): rotate planar error into base_link, control every axis,
        # and implement the required resettable yaw PID state outside this pure
        # P-controller baseline.
        forward=clamp(gains.position_kp * error_x, gains.max_linear),
        reached=False,
    )
