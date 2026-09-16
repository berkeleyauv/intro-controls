"""Publish a non-mutating readiness summary for the provided Unity stack."""

import json
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger

from tardigrade_interfaces.msg import RobotStatus


REQUIRED_SERVICES = (
    "/tardigrade/set_armed",
    "/tardigrade/set_external_control",
    "/tardigrade/sim/reset",
)


class ReadinessMonitor(Node):
    """Check transport, live streams, and services without changing state."""

    def __init__(self):
        super().__init__("readiness_monitor")
        self.declare_parameter("freshness_sec", 1.0)
        self.declare_parameter(
            "odometry_topic", "/tardigrade/state/odometry/filtered"
        )
        self._received = {"clock": None, "status": None, "odometry": None}
        self._robot_connected = False
        self._armed = False
        self._external_control = False
        self._last_report = None

        self.create_subscription(
            Clock, "/clock", lambda _: self._mark("clock"), qos_profile_sensor_data
        )
        self.create_subscription(
            Odometry,
            str(self.get_parameter("odometry_topic").value),
            lambda _: self._mark("odometry"),
            qos_profile_sensor_data,
        )
        self.create_subscription(
            RobotStatus, "/tardigrade/status", self._on_status, 10
        )

        latched = QoSProfile(depth=1)
        latched.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._ready_publisher = self.create_publisher(
            Bool, "/tardigrade/intro/ready", latched
        )
        self._detail_publisher = self.create_publisher(
            String, "/tardigrade/intro/readiness", latched
        )
        self.create_service(
            Trigger,
            "/tardigrade/intro/check_readiness",
            self._check_readiness,
        )
        self.create_timer(0.5, self._publish)

    def _mark(self, stream):
        self._received[stream] = time.monotonic()

    def _on_status(self, message):
        self._mark("status")
        self._robot_connected = bool(message.control_connected)
        self._armed = bool(message.armed)
        self._external_control = bool(message.external_control_enabled)

    def _snapshot(self):
        now = time.monotonic()
        freshness = max(
            0.1, float(self.get_parameter("freshness_sec").value)
        )
        streams = {
            name: received is not None and now - received <= freshness
            for name, received in self._received.items()
        }
        discovered = {name for name, _ in self.get_service_names_and_types()}
        services = {name: name in discovered for name in REQUIRED_SERVICES}
        ready = (
            all(streams.values())
            and all(services.values())
            and self._robot_connected
        )
        report = {
            "ready": ready,
            "streams": streams,
            "services": services,
            "unity_control_connected": self._robot_connected,
            "armed": self._armed,
            "external_control_enabled": self._external_control,
        }
        return ready, json.dumps(report, sort_keys=True)

    def _publish(self):
        ready, report = self._snapshot()
        ready_message = Bool()
        ready_message.data = ready
        detail_message = String()
        detail_message.data = report
        self._ready_publisher.publish(ready_message)
        self._detail_publisher.publish(detail_message)
        if report != self._last_report:
            log = self.get_logger().info if ready else self.get_logger().warn
            log(report)
            self._last_report = report

    def _check_readiness(self, _, response):
        response.success, response.message = self._snapshot()
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ReadinessMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
