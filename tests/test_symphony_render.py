"""Real bespoke meshes use the same LED inverse projection and original image UV."""
import json
import os
import subprocess
import pytest
from PIL import Image
from studio.config import Config
from studio.server import ROOT, blender_binary


def test_symphony_is_additive_and_retains_bupt_default():
    default = Config()
    assert default.frame.template == "aurora_float"
    specific = Config.model_validate_json(
        (ROOT / "configs/autumn-symphony.json").read_text()
    )
    assert specific.frame.template == "autumn_symphony"
    assert specific.screen == default.screen and specific.camera == default.camera


@pytest.mark.skipif(
    os.environ.get("RUN_BLENDER_TESTS") != "1", reason="actual Blender render"
)
@pytest.mark.parametrize("shape", ["landscape", "portrait", "convex"])
def test_symphony_actual_mapping(tmp_path, shape):
    c = Config.model_validate_json((ROOT / "configs/autumn-symphony.json").read_text())
    c.render.scale = 0.125
    c.render.samples = 16
    poster = ROOT / "examples/v2/jiqi-qiuyun/original.png"
    if shape == "portrait":
        poster = tmp_path / "portrait.png"
        Image.new("RGB", (600, 1000), "#aab9c8").save(poster)
    elif shape == "convex":
        c.screen.curvature = "convex"
        c.camera.position = [12, -14, 2]
        c.camera.target = [0, 0, 0]
        c.camera.fov_deg = 65
    cfg = tmp_path / "config.json"
    cfg.write_text(c.model_dump_json())
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
            str(cfg),
            "--poster",
            str(poster),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    r = json.loads((out / "report.json").read_text())
    a = r["artwork"]
    assert r["passed"] and r["metrics"]["foreground_coverage"] >= 0.98
    assert a["template"] == "autumn_symphony" and a["poster_aspect_preserved"]
    assert a["uv_crop"] == [0, 0, 1, 1]
    assert a["source_aspect"] == pytest.approx(a["display_aspect"])
    assert a["architectural_geometry"]["projected_decoration_guard_all_pass"]
    assert Image.open(out / "atlas.png").size == (546, 390)
    assert (out / "scene.blend").is_file()
