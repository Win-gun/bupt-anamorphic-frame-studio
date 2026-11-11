"""Opt-in actual V3 renders; numerical acceptance is separate from visual review."""
import json
import os
import subprocess
from pathlib import Path
import pytest
from PIL import Image
from studio.config import Config
from studio.server import ROOT, blender_binary
from studio.previews import make_previews

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BLENDER_TESTS") != "1",
    reason="actual Blender V3 renders require RUN_BLENDER_TESTS=1",
)


@pytest.mark.parametrize(
    "template,poster,convex",
    [
        ("aurora_float", "examples/v2/jiqi-qiuyun/original.png", False),
        ("aurora_float", "examples/v3/fixtures/light-landscape.png", False),
        ("aurora_float", "examples/v3/fixtures/dark-portrait.png", False),
        ("aurora_float", "examples/poster.png", True),
        ("soft_depth", "examples/v2/jiqi-qiuyun/original.png", False),
        ("glass_layers", "examples/v2/jiqi-qiuyun/original.png", False),
        ("embedded_cube", "examples/v2/jiqi-qiuyun/original.png", False),
    ],
)
def test_v3_actual_preserved_poster_and_mapping(tmp_path, template, poster, convex):
    c = Config()
    c.frame.template = template
    c.render.scale = 0.125
    c.render.samples = 16
    # Exercise both geometries independent of the product's default preset.
    c.screen.curvature = "convex" if convex else "concave"
    c.camera.position = [12, -14, 2] if convex else [-2, -14, 2]
    c.camera.target = [0, 0, 0]
    c.camera.fov_deg = 65
    config = tmp_path / "config.json"
    config.write_text(c.model_dump_json())
    target = tmp_path / "out"
    process = subprocess.run(
        [
            blender_binary(),
            "-b",
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "studio/blender_render.py"),
            "--",
            "--config",
            str(config),
            "--poster",
            str(ROOT / poster),
            "--output",
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads((target / "report.json").read_text())
    assert report["passed"], report["metrics"]
    assert report["artwork"]["poster_aspect_preserved"]
    width, height = report["artwork"]["poster_display_metres"]
    with Image.open(ROOT / poster) as source:
        assert width / height == pytest.approx(source.width / source.height)
    assert Image.open(target / "atlas.png").size == (546, 390)
    assert (target / "scene.blend").is_file() and (target / "scene.glb").is_file()
    make_previews(target)
    image = Image.open(target / "simulation_rgba.png")
    assert (
        image.getpixel((0, 0))[3] == 0
    ), "physical mask must have truly black world outside screen"
    assert (
        json.loads((target / "preview.json").read_text())["playback_canvas_changed"]
        is False
    )
