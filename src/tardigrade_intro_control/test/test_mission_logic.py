from tardigrade_intro_control.mission_logic import (
    GateMissionLogic,
    GateObservation,
    MissionConfig,
    MissionPhase,
)


def visible_gate(yaw=0.0, distance=3.0):
    return GateObservation(True, 0.9, yaw, distance)


def test_searches_without_gate():
    mission = GateMissionLogic()
    mission.start()
    command = mission.update(None, now_sec=0.0)
    assert mission.phase == MissionPhase.SEARCH
    assert command.yaw > 0.0


def test_aligns_before_approaching():
    mission = GateMissionLogic()
    mission.start()
    command = mission.update(visible_gate(yaw=0.3), now_sec=0.0)
    assert mission.phase == MissionPhase.ALIGN
    assert command.forward == 0.0
    assert command.yaw > 0.0


def test_stale_observation_is_rejected():
    mission = GateMissionLogic()
    mission.start()
    stale = GateObservation(True, 0.9, 0.0, 3.0, age_sec=10.0)
    command = mission.update(stale, now_sec=0.0)
    assert mission.phase == MissionPhase.SEARCH
    assert command.forward == 0.0


def test_transit_finishes_after_duration():
    config = MissionConfig(transit_duration_sec=2.0)
    mission = GateMissionLogic(config)
    mission.start()
    mission.update(visible_gate(distance=1.0), now_sec=5.0)
    assert mission.phase == MissionPhase.TRANSIT
    mission.update(visible_gate(distance=1.0), now_sec=7.1)
    assert mission.phase == MissionPhase.COMPLETE
