"""The art preset shares geometry and validates the entire oriented emitter."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from studio.autumn_resonance import (
    DEFAULTS,
    VARIANTS,
    architecture_plan,
    artistic_plan,
    effective_config,
    emitter_samples,
)

ROOT = Path(__file__).resolve().parents[1]


def config():
    cfg = json.loads((ROOT / "examples/embedded-cube/floating-config.json").read_text())
    cfg["frame"]["template"] = "autumn_resonance_cube"
    return cfg


def test_art_preset_reuses_exact_cube_geometry_and_full_uv():
    cfg = config()
    original = copy.deepcopy(cfg)
    effective = effective_config(cfg)
    plan = architecture_plan(effective, (4535, 2551))
    assert cfg == original
    assert plan["poster_z"] == pytest.approx(-2.1)
    assert plan["depth"] + plan["poster_z"] == pytest.approx(0.9)
    assert plan["composition"]["uv_crop"] == [0, 0, 1, 1]
    assert plan["poster_width"] / plan["poster_height"] == pytest.approx(4535 / 2551)
    assert plan["composition"]["metrics"]["opening_safe"]


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("depth", [1.0, 3.0, 6.0])
@pytest.mark.parametrize("softness", [0.1, 0.8, 1.0])
def test_whole_emitter_discs_stay_out_of_solids(variant, depth, softness):
    cfg = config()
    cfg["cube"]["depth_m"] = depth
    cfg["autumn"] = dict(variant=variant, softness=softness)
    cfg = effective_config(cfg)
    geometry = architecture_plan(cfg, (4535, 2551))
    art = artistic_plan(cfg, geometry)
    assert len(art["lights"]) == 6
    w, h, d, t = (geometry[k] for k in ("width", "height", "depth", "wall_thickness"))
    for lamp in art["lights"]:
        assert lamp["entire_emitter_inside_free_space"]
        assert lamp["diameter_m"] > 0
        points = emitter_samples(
            lamp["position"], lamp["target"], lamp["diameter_m"], 2048
        )
        if lamp["name"] == "facade":
            assert np.all(points[:, 2] > 0)
        else:
            assert np.all(points > [-w / 2, -h / 2, -d])
            assert np.all(points < [w / 2, h / 2, -t])


def test_variants_preserve_geometry_camera_and_change_lighting():
    cfg = config()
    results = []
    for variant in VARIANTS:
        cfg["autumn"] = dict(variant=variant)
        effective = effective_config(cfg)
        plan = architecture_plan(effective, (4535, 2551))
        results.append((plan, artistic_plan(effective, plan)))
    assert all(p == results[0][0] for p, _ in results)
    assert len({art["lights"][1]["energy_w"] for _, art in results}) == 3
