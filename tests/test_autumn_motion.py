"""Pure numerical motion tests; actual Blender/LED coverage remains integration QA."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from studio.autumn_motion import (
    motion_state,
    translation,
    validate_geometry,
    checkpoints,
)
from studio.autumn_resonance import effective_config
from studio.embedded_cube_scene import architecture_plan


def setup_geometry(size):
    config = json.loads(Path("configs/autumn-resonance.json").read_text())
    plan = architecture_plan(effective_config(config), size)
    room = plan["opening"]
    cavity = dict(
        opening_ndc=room["opening_ndc"],
        opening_safe=room["metrics"]["opening_safe"],
        front_plane_center=room["center"],
        opening_width_m=plan["width"],
        opening_height_m=plan["height"],
        cavity_depth_m=plan["depth"],
        wall_thickness_m=plan["wall_thickness"],
        panel_total_envelope_m=0.025,
    )
    return config, plan["composition"], cavity


def test_stage_boundaries_and_hold():
    for t, forward, up, light in [
        (0, 0, 0, 0.55),
        (1.5, 0, 0, 1),
        (3.5, 0.2, 0, 1),
        (4.25, 0.2, 0.05, 1),
        (5, 0.2, 0, 1),
        (7.5, 0.2, 0, 1),
    ]:
        state = motion_state(t)
        assert [
            state["forward_m"],
            state["up_m"],
            state["light_factor"],
        ] == pytest.approx([forward, up, light])
    states = [motion_state(i / 24) for i in range(180)]
    assert all(s["stage"] == "stable_hold" for s in states[120:])
    assert (
        len({(s["forward_m"], s["up_m"], s["light_factor"]) for s in states[120:]}) == 1
    )
    assert np.diff([s["light_factor"] for s in states]).min() >= 0
    assert np.diff([s["forward_m"] for s in states]).min() >= 0


@pytest.mark.parametrize(
    "size", [(1600, 900), (900, 1600), (1000, 1000), (2400, 600), (600, 2400)]
)
def test_all_180_solid_envelopes_are_inside_room_and_safe_opening(size):
    config, c, cavity = setup_geometry(size)
    for i in range(180):
        state = motion_state(i / 180 * 7.5)
        metrics = validate_geometry(config, c, cavity, translation(state, c))
        assert metrics["passed"], (size, i, metrics)
        assert metrics["panel_envelope_m"] == 0.025
        assert metrics["front_distance_m"] > cavity["wall_thickness_m"] + 0.08
        assert metrics["rear_clearance_m"] > 0


def test_unsafe_geometry_fails_closed():
    config, c, cavity = setup_geometry((900, 1600))
    for direction, distance in [
        ("normal", 3),
        ("normal", -3),
        ("up", 20),
        ("right", 20),
    ]:
        assert not validate_geometry(
            config, c, cavity, np.array(c[direction]) * distance
        )["passed"]
    unsafe = copy.deepcopy(cavity)
    unsafe["opening_safe"] = False
    assert not validate_geometry(config, c, unsafe, [0, 0, 0])["passed"]
    assert not validate_geometry(config, c, cavity, [float("nan"), 0, 0])["passed"]


def test_checkpoints_include_all_stages_peak_and_hold():
    assert checkpoints() == [0, 36, 84, 102, 120, 150, 179]
    assert checkpoints(6) == [0, 1, 3, 4, 5]
    for count in (6, 180, 300):
        assert all(0 <= i < count for i in checkpoints(count))
        hold = [
            motion_state(i / count * 7.5) for i in range(count) if i / count * 7.5 >= 5
        ]
        assert all(
            s["up_m"] == 0 and s["forward_m"] == 0.2 and s["light_factor"] == 1
            for s in hold
        )
