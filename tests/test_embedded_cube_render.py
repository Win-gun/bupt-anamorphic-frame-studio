"""Actual architectural cube camera projection and saved-scene regressions."""
import os, json, subprocess
import pytest
from PIL import Image
from studio.config import Config
from studio.server import ROOT, blender_binary

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BLENDER_TESTS") != "1", reason="actual Blender renders"
)


@pytest.mark.parametrize(
    "layout,convex", [("floating", False), ("back_wall", False), ("floating", True)]
)
def test_new_cube_actual_pipeline(tmp_path, layout, convex):
    c = Config()
    c.frame.template = "embedded_cube_architecture"
    c.cube.layout = layout
    c.render.scale = 0.125
    c.render.samples = 16
    # Exercise both geometries independent of the product's default preset.
    c.screen.curvature = "convex" if convex else "concave"
    c.camera.position = [12, -14, 2] if convex else [-2, -14, 2]
    c.camera.target = [0, 0, 0]
    c.camera.fov_deg = 65
    p = tmp_path / "config.json"
    p.write_text(c.model_dump_json())
    out = tmp_path / "out"
    run = subprocess.run(
        [
            blender_binary(),
            "-b",
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "studio/blender_render.py"),
            "--",
            "--config",
            str(p),
            "--poster",
            str(ROOT / "examples/v2/jiqi-qiuyun/original.png"),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    r = json.loads((out / "report.json").read_text())
    assert r["passed"], r["metrics"]
    a = r["artwork"]
    g = a["architectural_geometry"]
    assert a["poster_aspect_preserved"] and a["uv_crop"] == [0, 0, 1, 1]
    assert g["continuous_facade"] and g["solid_interior_walls"] == 5
    assert g["layout"] == layout and g["opening_safe"]
    assert a["poster_display_metres"][0] / a["poster_display_metres"][
        1
    ] == pytest.approx(4535 / 2551)
    assert Image.open(out / "atlas.png").size == (546, 390)
    assert (out / "scene.blend").stat().st_size > 1000
