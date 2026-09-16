"""Safe action lifecycle around the intentionally incomplete pose controller."""

import math
import threading
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

from tardigrade_interfaces.msg import RobotStatus
from tardigrade_intro_interfaces.action import MoveToPose

from tardigrade_intro_control.control_math import (
    BodyCommand,
    ControllerGains,
    PoseState,
    compute_pose_command,
    wrap_angle,
    yaw_from_quaternion,
)


def yaw_from_message(quaternion):
    return yaw_from_quaternion(
        quaternion.x, quaternion.y, quaternion.z, quaternion.w
    )


def duration_seconds(duration):
    return float(duration.sec) + float(duration.nanosec) / 1e9


class MoveToPoseServer(Node):
    """Publish bounded mission velocity commands while one action is active."""

    def __init__(self):
        super().__init__("move_to_pose_server")
        self.declare_parameter(
            "odometry_topic", "/tardigrade/state/odometry/filtered"
        )
        self.declare_parameter(
            "command_topic", "/tardigrade/control/velocity_setpoint/mission"
        )
        self.declare_parameter("control_rate_hz", 20.0)
        self.declare_parameter("feedback_rate_hz", 5.0)
        self.declare_parameter("odometry_timeout_sec", 0.4)
        self.declare_parameter("settle_time_sec", 1.0)
        self.declare_parameter("position_kp", 0.45)
        self.declare_parameter("depth_kp", 0.6)
        self.declare_parameter("yaw_pid.kp", 0.8)
        self.declare_parameter("yaw_pid.ki", 0.0)
        self.declare_parameter("yaw_pid.kd", 0.0)
        self.declare_parameter("yaw_pid.integral_limit", 0.5)
        self.declare_parameter("yaw_pid.output_limit", 0.3)
        self.declare_parameter("yaw_pid.derivative_filter_alpha", 0.2)
        self.declare_parameter("max_linear", 0.35)
        self.declare_parameter("max_vertical", 0.25)
        self.declare_parameter("position_tolerance", 0.12)
        self.declare_parameter("depth_tolerance", 0.08)
        self.declare_parameter("yaw_tolerance", 0.08)

        self._callback_group = ReentrantCallbackGroup()
        self._lock = threading.Lock()
        self._latest_odometry = None
        self._odometry_received_at = None
        self._plant_permitted = False
        self._goal_reserved = False
        self._target = None
        self._within_tolerance_since = None
        self._controller_state = "idle"
        self._last_errors = (math.nan, math.nan)

        self.create_subscription(
            Odometry,
            str(self.get_parameter("odometry_topic").value),
            self._on_odometry,
            qos_profile_sensor_data,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            RobotStatus,
            "/tardigrade/status",
            self._on_status,
            10,
            callback_group=self._callback_group,
        )
        self._command_publisher = self.create_publisher(
            TwistStamped,
            str(self.get_parameter("command_topic").value),
            10,
        )
        self._state_publisher = self.create_publisher(
            String, "/tardigrade/intro/controller_state", 10
        )
        rate = max(1.0, float(self.get_parameter("control_rate_hz").value))
        self.create_timer(
            1.0 / rate, self._control, callback_group=self._callback_group
        )
        self._action_server = ActionServer(
            self,
            MoveToPose,
            "/tardigrade/intro/move_to_pose",
            execute_callback=self._execute,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self._callback_group,
        )

    def _gains(self):
        return ControllerGains(
            position_kp=float(self.get_parameter("position_kp").value),
            depth_kp=float(self.get_parameter("depth_kp").value),
            yaw_kp=float(self.get_parameter("yaw_pid.kp").value),
            max_linear=abs(float(self.get_parameter("max_linear").value)),
            max_vertical=abs(float(self.get_parameter("max_vertical").value)),
            max_yaw=abs(
                float(self.get_parameter("yaw_pid.output_limit").value)
            ),
            position_tolerance=abs(
                float(self.get_parameter("position_tolerance").value)
            ),
            depth_tolerance=abs(
                float(self.get_parameter("depth_tolerance").value)
            ),
            yaw_tolerance=abs(
                float(self.get_parameter("yaw_tolerance").value)
            ),
        )

    def _on_odometry(self, message):
        try:
            yaw_from_message(message.pose.pose.orientation)
        except ValueError as error:
            self.get_logger().error(f"Rejected invalid odometry: {error}")
            return
        with self._lock:
            self._latest_odometry = message
            self._odometry_received_at = time.monotonic()

    def _on_status(self, message):
        permitted = bool(
            message.control_connected
            and message.armed
            and message.external_control_enabled
        )
        with self._lock:
            self._plant_permitted = permitted

    def _goal_callback(self, request):
        try:
            target = request.target
            timeout = duration_seconds(request.timeout)
            position = target.pose.position
            if target.header.frame_id != "odom":
                raise ValueError("target.header.frame_id must be 'odom'")
            if not all(
                math.isfinite(value)
                for value in (position.x, position.y, position.z)
            ):
                raise ValueError("target position must be finite")
            yaw_from_message(target.pose.orientation)
            if not math.isfinite(timeout) or timeout <= 0.0:
                raise ValueError("timeout must be greater than zero")
        except ValueError as error:
            self.get_logger().warn(f"Rejected MoveToPose goal: {error}")
            return GoalResponse.REJECT

        now = time.monotonic()
        odometry_timeout = float(
            self.get_parameter("odometry_timeout_sec").value
        )
        with self._lock:
            odometry_fresh = (
                self._odometry_received_at is not None
                and now - self._odometry_received_at <= odometry_timeout
            )
            unavailable = (
                self._goal_reserved
                or not odometry_fresh
                or not self._plant_permitted
            )
            if unavailable:
                self.get_logger().warn(
                    "Rejected MoveToPose goal: require no active goal, fresh "
                    "odometry, and armed/external-control simulator status"
                )
                return GoalResponse.REJECT
            self._goal_reserved = True
        return GoalResponse.ACCEPT

    def _cancel_callback(self, _):
        return CancelResponse.ACCEPT

    def _pose_state(self, message):
        pose = message.pose.pose
        return PoseState(
            x=float(pose.position.x),
            y=float(pose.position.y),
            z=float(pose.position.z),
            yaw=yaw_from_message(pose.orientation),
        )

    def _control(self):
        now = time.monotonic()
        odometry_timeout = float(
            self.get_parameter("odometry_timeout_sec").value
        )
        with self._lock:
            target = self._target
            odometry = self._latest_odometry
            received_at = self._odometry_received_at
            permitted = self._plant_permitted
        if target is None:
            return
        if not permitted:
            self._set_state("safety_gate_closed")
            self._publish_neutral()
            return
        odometry_stale = (
            odometry is None
            or received_at is None
            or now - received_at > odometry_timeout
        )
        if odometry_stale:
            self._set_state("stale_odometry")
            self._publish_neutral()
            return

        current = self._pose_state(odometry)
        command = compute_pose_command(current, target, self._gains())
        position_error = math.sqrt(
            (target.x - current.x) ** 2
            + (target.y - current.y) ** 2
            + (target.z - current.z) ** 2
        )
        yaw_error = wrap_angle(target.yaw - current.yaw)
        with self._lock:
            self._last_errors = (position_error, yaw_error)
            if command.reached:
                if self._within_tolerance_since is None:
                    self._within_tolerance_since = now
                settled = now - self._within_tolerance_since >= float(
                    self.get_parameter("settle_time_sec").value
                )
                self._controller_state = "reached" if settled else "settling"
            else:
                self._within_tolerance_since = None
                self._controller_state = "controlling"
        self._publish_command(command)
        self._publish_state()

    def _publish_command(self, command):
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_link"
        message.twist.linear.x = float(command.forward)
        message.twist.linear.y = float(command.left)
        message.twist.linear.z = float(command.up)
        message.twist.angular.z = float(command.yaw)
        self._command_publisher.publish(message)

    def _publish_neutral(self):
        self._publish_command(BodyCommand())

    def _set_state(self, state):
        with self._lock:
            self._controller_state = state
            self._within_tolerance_since = None
        self._publish_state()

    def _publish_state(self):
        with self._lock:
            state = self._controller_state
        message = String()
        message.data = state
        self._state_publisher.publish(message)

    def _result(self, success, message):
        result = MoveToPose.Result()
        result.success = bool(success)
        result.message = message
        with self._lock:
            result.final_position_error = float(self._last_errors[0])
            result.final_yaw_error = float(self._last_errors[1])
        return result

    def _feedback(self):
        feedback = MoveToPose.Feedback()
        with self._lock:
            odometry = self._latest_odometry
            feedback.position_error = float(self._last_errors[0])
            feedback.yaw_error = float(self._last_errors[1])
            feedback.controller_state = self._controller_state
        if odometry is not None:
            feedback.current_position = odometry.pose.pose.position
        return feedback

    def _execute(self, goal_handle):
        request = goal_handle.request
        target_pose = request.target.pose
        target = PoseState(
            x=float(target_pose.position.x),
            y=float(target_pose.position.y),
            z=float(target_pose.position.z),
            yaw=yaw_from_message(target_pose.orientation),
        )
        started = time.monotonic()
        deadline = started + duration_seconds(request.timeout)
        feedback_period = 1.0 / max(
            1.0, float(self.get_parameter("feedback_rate_hz").value)
        )
        with self._lock:
            self._target = target
            self._within_tolerance_since = None
            self._last_errors = (math.nan, math.nan)
            self._controller_state = "starting"
        self.get_logger().info("Accepted MoveToPose goal")

        try:
            while rclpy.ok():
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    return self._result(False, "goal canceled")
                now = time.monotonic()
                with self._lock:
                    state = self._controller_state
                if state == "reached":
                    goal_handle.succeed()
                    return self._result(True, "target reached and settled")
                if state in ("stale_odometry", "safety_gate_closed"):
                    goal_handle.abort()
                    return self._result(False, state.replace("_", " "))
                if now >= deadline:
                    goal_handle.abort()
                    return self._result(False, "goal timeout")
                goal_handle.publish_feedback(self._feedback())
                time.sleep(feedback_period)

            goal_handle.abort()
            return self._result(False, "ROS shutdown")
        finally:
            self._publish_neutral()
            with self._lock:
                self._target = None
                self._within_tolerance_since = None
                self._controller_state = "idle"
                self._goal_reserved = False
            self._publish_state()

    def destroy_node(self):
        self._publish_neutral()
        self._action_server.destroy()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MoveToPoseServer()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
