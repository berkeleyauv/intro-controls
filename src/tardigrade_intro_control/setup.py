import os
from glob import glob

from setuptools import setup


package_name = "tardigrade_intro_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Berkeley AUV",
    maintainer_email="software@berkeleyauv.org",
    description="Simulation-only controls onboarding project.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            (
                "move_to_pose_server = "
                "tardigrade_intro_control.move_to_pose_server:main"
            ),
            (
                "readiness_monitor = "
                "tardigrade_intro_control.readiness_monitor:main"
            ),
        ],
    },
)
