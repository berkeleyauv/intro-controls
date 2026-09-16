"""One-axis educational PID seam used by the yaw-loop milestone."""

from dataclasses import dataclass
import math

from tardigrade_intro_control.control_math import clamp


@dataclass(frozen=True)
class PidConfig:
    kp: float
    ki: float
    kd: float
    integral_limit: float
    output_limit: float
    derivative_filter_alpha: float = 0.2


@dataclass(frozen=True)
class PidStep:
    output: float
    p_term: float
    i_term: float
    d_term: float
    saturated: bool


class PidController:
    """Runnable P-only baseline that students extend to a complete PID."""

    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.previous_measurement = None
        self.filtered_derivative = 0.0

    def update(self, error, measurement, dt):
        if not all(math.isfinite(value) for value in (error, measurement, dt)):
            raise ValueError("PID inputs must be finite")
        if dt <= 0.0:
            raise ValueError("PID dt must be greater than zero")

        p_term = self.config.kp * error

        # TODO(project): integrate error with a limit and anti-windup. Compute a
        # filtered derivative on measurement (not a setpoint kick), then store
        # the state required by the next call. Reset must clear all that state.
        i_term = 0.0
        d_term = 0.0

        raw_output = p_term + i_term + d_term
        output = clamp(raw_output, abs(self.config.output_limit))
        return PidStep(
            output=output,
            p_term=p_term,
            i_term=i_term,
            d_term=d_term,
            saturated=abs(raw_output) > abs(self.config.output_limit),
        )
