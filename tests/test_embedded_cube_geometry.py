import copy
import json
from pathlib import Path
import numpy as np
import pytest
from studio.embedded_cube_scene import architecture_plan, facade_mesh

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    cfg = json.loads((ROOT / "configs/bupt-curved-led.json").read_text())
    cfg["frame"]["template"] = "embedded_cube_architecture"
    cfg["cube"] = {
        "layout": "floating",
        "depth_m": 3.0,
        "wall_thickness_m": 0.32,
        "opening_scale": 0.94,
        "poster_scale": 0.78,
        "poster_depth_fraction": 0.62,
    }
    return cfg


@pytest.mark.parametrize("layout", ["floating", "back_wall"])
def test_original_full_uv_and_safe_architectural_opening(config, layout):
    config["cube"]["layout"] = layout
    p = architecture_plan(config, (4535, 2551))
    c = p["composition"]
    assert c["metrics"]["opening_safe"]
    assert p["opening"]["metrics"]["opening_safe"]
    assert c["uv_crop"] == [0, 0, 1, 1]
    assert p["poster_width"] / p["poster_height"] == pytest.approx(4535 / 2551)
    assert p["width"] / p["height"] == pytest.approx(1.5)
    assert p["poster_width"] < p["width"]
    assert p["poster_height"] < p["height"]
    assert -0.32 > p["poster_z"] > -3


def test_two_layouts_are_physically_distinct(config):
    a = architecture_plan(config, (4535, 2551))
    config["cube"]["layout"] = "back_wall"
    b = architecture_plan(config, (4535, 2551))
    assert a["depth"] + a["poster_z"] == pytest.approx(1.14)
    assert b["depth"] + b["poster_z"] == pytest.approx(0.055)
    assert a["composition"]["opening_ndc"] != b["composition"]["opening_ndc"]


def test_facade_is_one_closed_connected_solid():
    vertices, faces = facade_mesh(8, 5, 12, 0.32)
    edges = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            key = tuple(sorted([a, b]))
            edges[key] = edges.get(key, 0) + 1
    assert len(vertices) == 16
    assert set(edges.values()) == {2}
    assert len(vertices) - len(edges) + len(faces) == 0  # solid annulus has one hole
    assert {v[2] for v in vertices} == {0, -0.32}


def test_planner_does_not_mutate_config(config):
    before = copy.deepcopy(config)
    architecture_plan(config, (4535, 2551))
    assert config == before


def test_facade_outward_normals_and_physical_volume():
    vertices, faces = facade_mesh(8, 5, 12, 0.32)
    v = np.asarray(vertices)
    volume = 0
    for face in faces:
        for i in range(1, len(face) - 1):
            volume += np.dot(v[face[0]], np.cross(v[face[i]], v[face[i + 1]])) / 6
    assert volume == pytest.approx(((8 + 24) * (5 + 24) - 8 * 5) * 0.32)


def test_extreme_image_scale_remains_inside_chamber(config):
    config["frame"]["scale"] = 1
    config["cube"]["poster_scale"] = 0.85
    p = architecture_plan(config, (700, 1400))
    assert p["poster_width"] <= p["width"] * 0.9 + 1e-8
    assert p["poster_height"] <= p["height"] * 0.9 + 1e-8
    assert p["composition"]["metrics"]["opening_safe"]


def test_presets_retain_all_existing_templates():
    from studio.scene_design import AURORA_TEMPLATES, LEGACY_TEMPLATES

    assert {
        "aurora_float",
        "soft_depth",
        "glass_layers",
        "embedded_cube",
    } <= AURORA_TEMPLATES
    assert {"cinema", "deep", "float", "glass"} == LEGACY_TEMPLATES
    from studio.config import Config

    c = Config()
    assert c.frame.template == "aurora_float"
    assert c.cube.layout == "floating"
