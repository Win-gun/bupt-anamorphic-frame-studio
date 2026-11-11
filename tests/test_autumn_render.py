"""Actual preview shaders and curved projection for the new art preset."""
import json
import os
import subprocess
import pytest
from PIL import Image
from studio.config import Config
from studio.server import ROOT, blender_binary

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BLENDER_TESTS") != "1", reason="actual Blender render"
)


@pytest.mark.parametrize("curvature", ["concave", "convex"])
def test_autumn_actual_curved_projection(tmp_path, curvature):
    c = Config()
    c.frame.template = "autumn_resonance_cube"
    c.screen.curvature = curvature
    c.render.scale = 0.125
    c.render.samples = 8
    c.render.quality = "quick"
    c.camera.position = [12, -14, 2] if curvature == "convex" else [-2, -14, 2]
    c.camera.target = [0, 0, 0]
    c.camera.fov_deg = 65
    p = tmp_path / "config.json"
    p.write_text(c.model_dump_json())
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
            str(tmp_path / "render"),
        ],
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    r = json.loads((tmp_path / "render/report.json").read_text())
    assert r["passed"] and r["metrics"]["foreground_coverage"] >= 0.98
    a = r["artwork"]
    assert a["template"] == "autumn_resonance_cube"
    assert a["uv_crop"] == [0, 0, 1, 1] and a["poster_aspect_preserved"]
    g = a["architectural_geometry"]
    assert g["poster_distance_from_front_m"] == pytest.approx(2.1)
    assert g["poster_gap_to_rear_wall_m"] == pytest.approx(0.9)
    assert len(a["lighting"]["lights"]) == 6
    assert a["material_nodes"]["metallic"] == 0
    assert Image.open(tmp_path / "render/atlas.png").size == (546, 390)
