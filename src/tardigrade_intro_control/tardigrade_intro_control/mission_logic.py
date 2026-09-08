"""A weak state-machine baseline to replace with a behavior tree."""

from dataclasses import dataclass
from enum import Enum

from tardigrade_intro_control.control_math import clamp


class MissionPhase(str, Enum):
    IDLE = "idle"
    SEARCH = "search"
    ALIGN = "align"
    APPROACH = "approach"
    TRANSIT = "transit"
    COMPLETE = "complete"
    ABORTED = "aborted"


@dataclass(frozen=True)
class GateObservation:
    visible: bool
    confidence: float
    yaw_error: float
    distance: float
    age_sec: float = 0.0


@dataclass(frozen=True)
class MissionConfig:
    confidence_threshold: float = 0.6
    observation_timeout_sec: float = 0.4
    alignment_tolerance: float = 0.08
    transit_distance: float = 1.2
    search_yaw: float = 0.2
    align_kp: float = 0.8
    max_yaw: float = 0.3
    approach_forward: float = 0.22
    transit_forward: float = 0.28
    transit_duration_sec: float = 4.0


@dataclass(frozen=True)
class MissionCommand:
    forward: float = 0.0
    yaw: float = 0.0


class GateMissionLogic:
    def __init__(self, config=MissionConfig()):
        self.config = config
        self.phase = MissionPhase.IDLE
        self._transit_started = None

    def start(self):
        if self.phase == MissionPhase.IDLE:
            self.phase = MissionPhase.SEARCH

    def reset(self):
        self.phase = MissionPhase.IDLE
        self._transit_started = None

    def abort(self):
        self.phase = MissionPhase.ABORTED

    def observation_is_usable(self, observation):
        return (
            observation is not None
            and observation.visible
            and observation.confidence >= self.config.confidence_threshold
            and observation.age_sec <= self.config.observation_timeout_sec
        )

    def update(self, observation, now_sec):
        if self.phase in (
            MissionPhase.IDLE,
            MissionPhase.COMPLETE,
            MissionPhase.ABORTED,
        ):
            return MissionCommand()

        usable = self.observation_is_usable(observation)
        if self.phase == MissionPhase.SEARCH:
            if usable:
                self.phase = MissionPhase.ALIGN
            else:
                return MissionCommand(yaw=self.config.search_yaw)

        if self.phase == MissionPhase.ALIGN:
            if not usable:
                self.phase = MissionPhase.SEARCH
                return MissionCommand()
            if abs(observation.yaw_error) <= self.config.alignment_tolerance:
                self.phase = MissionPhase.APPROACH
            else:
                return MissionCommand(
                    yaw=clamp(
                        self.config.align_kp * observation.yaw_error,
                        self.config.max_yaw,
                    )
                )

        if self.phase == MissionPhase.APPROACH:
            if not usable:
                self.phase = MissionPhase.SEARCH
                return MissionCommand()
            if observation.distance <= self.config.transit_distance:
                self.phase = MissionPhase.TRANSIT
                self._transit_started = now_sec
            else:
                return MissionCommand(
                    forward=self.config.approach_forward,
                    yaw=clamp(
                        self.config.align_kp * observation.yaw_error,
                        self.config.max_yaw,
                    ),
                )

        if self.phase == MissionPhase.TRANSIT:
            if now_sec - self._transit_started >= self.config.transit_duration_sec:
                self.phase = MissionPhase.COMPLETE
                return MissionCommand()
            return MissionCommand(forward=self.config.transit_forward)

        return MissionCommand()
