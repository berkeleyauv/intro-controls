"""ROS wrapper for the pure pose controller baseline."""

import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Bool, String

from tardigrade_intro_control.control_math import (
    ControllerGains,
    PoseState,
    compute_pose_command,
)


def yaw_from_quaternion(quaternion):
    return math.atan2(
        2.0 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y),
        1.0 - 2.0 * (quaternion.y * quaternion.y + quaternion.z * quaternion.z),
    )


class PoseController(Node):
    def __init__(self):
        super().__init__("intro_pose_controller")
        self.declare_parameter("odometry_topic", "/tardigrade/state/odometry")
        self.declare_parameter("command_topic", "/tardigrade/cmd_vel")
        self.declare_parameter("target_x", 2.0)
        self.declare_parameter("target_y", 0.0)
        self.declare_parameter("target_z", -1.0)
        self.declare_parameter("target_yaw", 0.0)
        self.declare_parameter("odometry_timeout_sec", 0.4)
        self.declare_parameter("control_rate_hz", 20.0)

        self.latest_odometry = None
        self.latest_odometry_ns = None
        self.enabled = False

        self.create_subscription(
            Odometry,
            self.get_parameter("odometry_topic").value,
            self.on_odometry,
            10,
        )
        self.create_subscription(
            Bool, "/tardigrade/intro/enabled", self.on_enabled, 10
        )
        self.command_pub = self.create_publisher(
            Twist, self.get_parameter("command_topic").value, 10
        )
        self.state_pub = self.create_publisher(
            String, "/tardigrade/intro/controller_state", 10
        )
        rate = float(self.get_parameter("control_rate_hz").value)
        self.create_timer(1.0 / max(rate, 1.0), self.control)

    def on_odometry(self, message):
        self.latest_odometry = message
        self.latest_odometry_ns = self.get_clock().now().nanoseconds

    def on_enabled(self, message):
        self.enabled = bool(message.data)

    def publish_state(self, value):
        message = String()
        message.data = value
        self.state_pub.publish(message)

    def control(self):
        output = Twist()
        if not self.enabled:
            self.command_pub.publish(output)
            self.publish_state("disabled")
            return
        if self.latest_odometry_ns is None:
            self.command_pub.publish(output)
            self.publish_state("waiting_for_odometry")
            return
        age_sec = (
            self.get_clock().now().nanoseconds - self.latest_odometry_ns
        ) / 1e9
        if age_sec > float(self.get_parameter("odometry_timeout_sec").value):
            self.command_pub.publish(output)
            self.publish_state("stale_odometry")
            return

        pose = self.latest_odometry.pose.pose
        current = PoseState(
            pose.position.x,
            pose.position.y,
            pose.position.z,
            yaw_from_quaternion(pose.orientation),
        )
        target = PoseState(
            float(self.get_parameter("target_x").value),
            float(self.get_parameter("target_y").value),
            float(self.get_parameter("target_z").value),
            float(self.get_parameter("target_yaw").value),
        )
        command = compute_pose_command(current, target, ControllerGains())
        output.linear.x = command.forward
        output.linear.y = command.left
        output.linear.z = command.up
        output.angular.z = command.yaw
        self.command_pub.publish(output)
        self.publish_state("reached" if command.reached else "controlling")


def main(args=None):
    rclpy.init(args=args)
    node = PoseController()
    try:
        rclpy.spin(node)
    finally:
        node.command_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
