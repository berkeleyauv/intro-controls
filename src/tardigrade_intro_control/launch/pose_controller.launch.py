import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("tardigrade_intro_control"),
        "config",
        "controller.yaml",
    )
    return LaunchDescription([
        Node(
            package="tardigrade_intro_control",
            executable="pose_controller",
            name="intro_pose_controller",
            output="screen",
            parameters=[config],
        ),
    ])
