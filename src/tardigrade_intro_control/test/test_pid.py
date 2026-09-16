import math

import pytest

from tardigrade_intro_control.pid import PidConfig, PidController


def controller():
    return PidController(
        PidConfig(
            kp=2.0,
            ki=0.5,
            kd=0.1,
            integral_limit=1.0,
            output_limit=0.3,
        )
    )


def test_pid_baseline_is_bounded():
    step = controller().update(error=10.0, measurement=0.0, dt=0.1)
    assert math.isclose(step.output, 0.3)
    assert step.saturated


def test_pid_rejects_invalid_dt():
    with pytest.raises(ValueError):
        controller().update(error=1.0, measurement=0.0, dt=0.0)


def test_pid_reset_clears_all_history():
    pid = controller()
    pid.integral = 0.7
    pid.previous_measurement = 1.0
    pid.filtered_derivative = 2.0
    pid.reset()
    assert pid.integral == 0.0
    assert pid.previous_measurement is None
    assert pid.filtered_derivative == 0.0
