# Rubric

| Area | Weight | Evidence |
|---|---:|---|
| Feedback-controller behavior | 30% | Error, settling, overshoot, control effort |
| ROS 2 integration | 20% | Correct topics, frames, parameters, launch and observability |
| Reactive mission behavior | 20% | Search, approach, transit and recovery |
| Safety and failure handling | 15% | Stale data, disable, cancellation, bounded commands |
| Tests and code quality | 10% | Focused tests and understandable decomposition |
| Communication | 5% | Plots, PR explanation and demo |

The controller is evaluated on randomized initial conditions and disturbances,
not just the nominal demonstration scenario.
